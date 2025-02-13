from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import pickle
import faiss
import unicodedata
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import requests
import json

app = Flask(__name__)
CORS(app)

# ---------------- Cargar y preparar el sistema de búsqueda ----------------

def cargar_sistema():
    """
    Carga el sistema de búsqueda deserializando el índice FAISS y la metadata almacenada.
    
    Retorna:
        dict: Diccionario con los datos del sistema de búsqueda.
    """
    try:
        with open('sistema_busqueda.pkl', 'rb') as f:
            data = pickle.load(f)
        data['index'] = faiss.deserialize_index(data['index'])
        return data
    except Exception as e:
        print(f"Error al cargar el sistema: {e}")
        return None

# ---------------- Funciones de procesamiento de texto ----------------

def normalizar_texto(texto):
    """
    Normaliza el texto eliminando tildes, caracteres especiales y convirtiéndolo a minúsculas.
    
    Parámetros:
        texto (str): Texto a normalizar.
    
    Retorna:
        str: Texto normalizado.
    """
    if not isinstance(texto, str):
        return ""
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

# ---------------- Función para verificar nombres de candidatos ----------------

def es_nombre_presidente(query, presidente):
    """
    Verifica si el nombre en la consulta coincide con el nombre de un candidato.
    
    Parámetros:
        query (str): Consulta del usuario.
        presidente (str): Nombre del candidato.
    
    Retorna:
        bool: True si el nombre coincide, False en caso contrario.
    """
    query_norm = normalizar_texto(query)
    presidente_norm = normalizar_texto(presidente)
    query_words = set(query_norm.split())
    presidente_words = set(presidente_norm.split())
    palabras_coincidentes = query_words.intersection(presidente_words)
    return query_norm in presidente_norm or presidente_norm in query_norm or len(palabras_coincidentes) >= 2

# ---------------- Cálculo de relevancia de documentos ----------------

def calcular_relevancia(query, texto, meta):
    """
    Calcula un puntaje de relevancia basado en la coincidencia de palabras clave,
    el tipo de documento, la exactitud y la posición de las palabras clave.
    
    Parámetros:
        query (str): Consulta del usuario.
        texto (str): Texto del documento.
        meta (dict): Metadata del documento.
    
    Retorna:
        float: Puntaje de relevancia del documento.
    """
    factores = {'palabras_clave': 0, 'exactitud': 0, 'tipo_doc': 0, 'posicion': 0, 'longitud': 0}
    texto_norm = normalizar_texto(texto)
    query_norm = normalizar_texto(query)
    query_words = set(query_norm.split())
    palabras_encontradas = sum(1 for word in query_words if word in texto_norm)
    factores['palabras_clave'] = palabras_encontradas / len(query_words) if query_words else 0

    # Verificar coincidencia exacta
    if query_norm in texto_norm:
        factores['exactitud'] = 1.0

    # Pesos por tipo de documento
    pesos_tipo = {'plan': 1.3, 'entrevista': 1.2, 'biografia': 1.0}
    peso_base = pesos_tipo.get(meta.get('tipo', ''), 1.0)

    # Ajuste para biografías con coincidencia de nombre
    if meta.get('tipo') == 'biografia' and es_nombre_presidente(query, meta.get('presidente', '')):
        peso_base *= 2.5
        factores['exactitud'] = 1.0

    factores['tipo_doc'] = peso_base

    # Posición de las palabras clave
    primera_aparicion = min((texto_norm.find(word) for word in query_words if word in texto_norm), default=len(texto_norm))
    factores['posicion'] = 1.0 - (primera_aparicion / len(texto_norm))

    # Factor de longitud
    palabras_texto = len(texto.split())
    factores['longitud'] = 1.0 if 10 <= palabras_texto <= 50 else 0.8

    # Pesos finales
    pesos = {'palabras_clave': 0.35, 'exactitud': 0.25, 'tipo_doc': 0.20, 'posicion': 0.15, 'longitud': 0.05}
    puntaje = sum(factor * pesos[nombre] for nombre, factor in factores.items())
    return puntaje

# ---------------- Función de búsqueda de documentos ----------------
def buscar(query, k=5, umbral_similitud=0.3):
    """
    Busca los documentos más relevantes en la base de datos utilizando coincidencias exactas y búsqueda semántica.
    
    Parámetros:
        query (str): Consulta del usuario.
        k (int): Número de resultados a devolver.
        umbral_similitud (float): Umbral de similitud para considerar documentos relevantes.
    
    Retorna:
        list: Lista de documentos relevantes ordenados por relevancia.
    """
    sistema = cargar_sistema()
    
    if sistema is None:
        print("❌ Sistema de búsqueda no inicializado")
        return []

    print(f"\n🔍 Query original: {query}")
    
    try:
        
        # Detectar tipo de consulta al inicio
        tipo_consulta, param = identificar_tipo_consulta(query)
        
        # Extraer nombre de la consulta y determinar si es biografía
        query_norm = normalizar_texto(query)
        nombre_buscado = query_norm
        es_consulta_biografia = False
        
        if tipo_consulta == 'biografia' or "biografia de" in query_norm or "quien es" in query_norm:
            es_consulta_biografia = True
            if "biografia de" in query_norm:
                nombre_buscado = query_norm.replace("biografia de", "").strip()
            elif "quien es" in query_norm:
                nombre_buscado = query_norm.replace("quien es", "").strip()
            else:
                nombre_buscado = param
        elif tipo_consulta == 'partido_candidato':
            nombre_buscado = param
            
            
        print(f"🎯 Buscando nombre: '{nombre_buscado}'")

        # Definir función de ordenamiento aquí para que esté disponible en todo el scope
        def clave_ordenamiento(x):
            tipo_peso = 1.0
            if es_consulta_biografia:
                tipo_peso = 3.0 if x['tipo'].lower() == 'biografia' else 1.0
            return (-tipo_peso * x['relevancia'], x['distancia_ajustada'])

        # Primero buscar coincidencias exactas
        resultados_exactos = []
        for idx, meta in enumerate(sistema['metadata']):
            nombre_presidente = normalizar_texto(meta['presidente'])
            if nombre_presidente == nombre_buscado:
                relevancia = calcular_relevancia(query, meta['texto_original'], meta)
                
                # Aumentar relevancia para biografías si es consulta de biografía
                if es_consulta_biografia and meta['tipo'].lower() == 'biografia':
                    relevancia *= 3.0
                elif tipo_consulta == 'partido_candidato':
                    relevancia *= 2.0  # Dar más peso a documentos del candidato buscado
                
                resultado = {
                    'distancia_original': 0,
                    'relevancia': relevancia,
                    'distancia_ajustada': 0,
                    'texto_original': meta['texto_original'],
                    'texto_contexto': meta['texto_contexto'],
                    'tipo': meta['tipo'],
                    'lista': meta['lista'],
                    'partido': meta['partido'],
                    'presidente': meta['presidente'],
                    'id_oracion': meta['id_oracion']
                }
                if meta['tipo'] == 'entrevista':
                    resultado.update({
                        'numero_entrevista': meta['numero_entrevista'],
                        'descripcion': meta['descripcion'],
                        'tema': meta['tema']
                    })
                resultados_exactos.append(resultado)

        # Si hay coincidencias exactas, ordenar y retornar
        if resultados_exactos:
            resultados_ordenados = sorted(resultados_exactos, key=clave_ordenamiento)[:k]
            
            print(f"\n✅ Encontradas {len(resultados_exactos)} coincidencias exactas")
            print("\n📝 Preview de documentos por coincidencia exacta:")
            for i, doc in enumerate(resultados_ordenados[:5], 1):
                print(f"\nDocumento {i}:")
                print(f"- Presidente: {doc['presidente']}")
                print(f"- Tipo: {doc['tipo']}")
                print(f"- Relevancia: {doc['relevancia']:.4f}")
                print(f"- Partido: {doc['partido']}")
            
            return resultados_ordenados

        print("\n⚠️ No se encontraron coincidencias exactas, usando búsqueda semántica...")

        # Si no hay coincidencias exactas, usar embeddings
        query_vec = sistema['vectorizer'].transform([query])
        similitudes = cosine_similarity(query_vec, sistema['tfidf_matrix']).flatten()
        indices_relevantes = np.where(similitudes > umbral_similitud)[0]

        if len(indices_relevantes) == 0:
            print("⚠️ Ningún documento supera el umbral de similitud")
            return []

        model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
        query_embedding = model.encode([query]).astype('float32')
        D, I = sistema['index'].search(query_embedding, k*2)

        resultados = []
        for i, (dist, idx) in enumerate(zip(D[0], I[0])):
            if idx < len(sistema['metadata']):
                meta = sistema['metadata'][idx]
                relevancia = calcular_relevancia(query, meta['texto_original'], meta)
                
                # Ajustar relevancia según el tipo de consulta
                if es_consulta_biografia and meta['tipo'].lower() == 'biografia':
                    relevancia *= 3.0
                elif tipo_consulta == 'partido_candidato':
                    # Aumentar relevancia si el documento corresponde al candidato buscado
                    nombre_presidente = normalizar_texto(meta['presidente'])
                    if nombre_buscado in nombre_presidente or nombre_presidente in nombre_buscado:
                        relevancia *= 2.0
                    
                    
                dist_ajustada = dist / (relevancia + 0.1)

                resultado = {
                    'distancia_original': dist,
                    'relevancia': relevancia,
                    'distancia_ajustada': dist_ajustada,
                    'texto_original': meta['texto_original'],
                    'texto_contexto': meta['texto_contexto'],
                    'tipo': meta['tipo'],
                    'lista': meta['lista'],
                    'partido': meta['partido'],
                    'presidente': meta['presidente'],
                    'id_oracion': meta['id_oracion']
                }

                if meta['tipo'] == 'entrevista':
                    resultado.update({
                        'numero_entrevista': meta['numero_entrevista'],
                        'descripcion': meta['descripcion'],
                        'tema': meta['tema']
                    })

                resultados.append(resultado)

        # Filtrar resultados si es una consulta de partido_candidato
        if tipo_consulta == 'partido_candidato':
            resultados = [r for r in resultados 
                         if nombre_buscado in normalizar_texto(r['presidente']) 
                         or normalizar_texto(r['presidente']) in nombre_buscado]
            
        # Usar la misma función de ordenamiento para resultados semánticos
        resultados_finales = sorted(resultados, key=clave_ordenamiento)[:k]

        print("\n📝 Preview de documentos por búsqueda semántica:")
        for i, doc in enumerate(resultados_finales[:5], 1):
            print(f"\nDocumento {i}:")
            print(f"- Presidente: {doc['presidente']}")
            print(f"- Tipo: {doc['tipo']}")
            print(f"- Relevancia: {doc['relevancia']:.4f}")
            print(f"- Partido: {doc['partido']}")

        return resultados_finales

    except Exception as e:
        print(f"❌ Error en búsqueda: {e}")
        return []

# Función para mostrar resultados de búsqueda
def mostrar_resultados(query, k=5):
    """
    Muestra los resultados de búsqueda en un formato estructurado.
    
    Parámetros:
    query (str): Consulta de búsqueda ingresada por el usuario.
    k (int): Número de resultados a mostrar. Por defecto, 5.
    
    Retorna:
    None: Imprime los resultados en consola.
    """
    print(f"\nBuscando: {query}")
    resultados = buscar(query, k)

    if not resultados:
        print("No se encontraron resultados relevantes.")
        return

    print("\nResultados encontrados:")
    for i, r in enumerate(resultados, 1):
        print(f"\nRanking: {i}")
        print(f"Tipo: {r['tipo']}")
        print(f"Lista: {r['lista']} - Partido: {r['partido']}")
        print(f"Presidente: {r['presidente']}")
        print(f"ID: {r['id_oracion']}")
        print(f"Relevancia: {r['relevancia']:.4f}")
        print("\nContexto:")
        print(r['texto_contexto'])

        if r['tipo'] == 'entrevista':
            print(f"\nNúmero de entrevista: {r['numero_entrevista']}")
            print(f"Tema: {r['tema']}")
            print(f"Descripción: {r['descripcion']}")

# Nuevas funciones para generación de respuesta
QUERY_PATTERNS = {
    'biografia': [
        r'^quien es (.+)',
        r'^quién es (.+)',
        r'^biografia de (.+)',
    ],
    'propuestas_verbo': [
        r'(?:que|qué) candidatos? proponen? (.+)',
        r'quienes? proponen? (.+)',
    ],
    'entrevista': [
        r'(?:que|qué) temas se tratan en (?:la )?entrevista de (.+)',
        r'(?:temas|tema) de (?:la )?entrevista de (.+)',
    ],
    'partido_candidato': [
        r'(?:el )?candidato (.+?) (?:a )?(?:que|qué|cual|cuál) partido pertenece',
        r'(.+?) (?:a )?(?:que|qué|cual|cuál) partido pertenece',
        r'(?:de )?(?:que|qué|cual|cuál) partido es (.+)',
        r'(.+?) partido' 
    ],
    'partido_nombre': [
        r'(?:que|qué|cual|cuál) candidatos? pertenecen? (?:a)?(?:l)? partido (.+)',
    ],
    'propuestas_candidato': [
        r'propuestas (?:del candidato )?(.+)',
        r'(?:que|qué) propone (.+)',
    ]
}

# ------------------------------
# Función para identificar el tipo de consulta
# ------------------------------
def identificar_tipo_consulta(query):
    """
    Identifica el tipo de consulta del usuario según patrones predefinidos.
    
    Parámetros:
    query (str): Consulta de búsqueda ingresada por el usuario.
    
    Retorna:
    tuple: (tipo de consulta, parámetro identificado)
    """
    query = query.lower().strip()
    
    for tipo, patrones in QUERY_PATTERNS.items():
        for patron in patrones:
            match = re.search(patron, query, re.IGNORECASE)
            if match:
                return tipo, match.group(1).strip()
    
    return "general", query

# ------------------------------
# Función para limpiar la consulta
# ------------------------------
def limpiar_query(query, tipo, param):
    """
    Limpia y ajusta la consulta según el tipo identificado.
    
    Parámetros:
    query (str): Consulta de búsqueda original.
    tipo (str): Tipo de consulta identificado.
    param (str): Parámetro extraído de la consulta.
    
    Retorna:
    str: Consulta ajustada.
    """
    if tipo == "biografia":
        return param
    elif tipo == "propuestas_verbo":
        return f"propuestas {param}"
    elif tipo == "entrevista":
        return f"entrevista {param}"
    elif tipo == "partido_candidato":
        return f"{param} partido"
    elif tipo == "partido_nombre":
        return f"partido {param}"
    elif tipo == "propuestas_candidato":
        return f"propuestas {param}"
    
    return query.lower().strip()


def generar_prompt_especifico(tipo, query, documentos):
    prompt_base = f"""Actúa como un asistente político especializado.
Genera una respuesta completa y directa basada en la siguiente información.

Pregunta: {query}

Documentos disponibles:"""

    for i, doc in enumerate(documentos, 1):
        prompt_base += f"""

[Documento {i}]
TIPO: {doc['tipo'].upper()}
CANDIDATO: {doc['presidente']}
PARTIDO: {doc['partido']}

CONTENIDO:
{doc['texto_contexto']}"""
        if doc['tipo'] == 'entrevista':
            prompt_base += f"\nTEMA: {doc.get('tema', 'No especificado')}"

    instrucciones = {
        'biografia': """
INSTRUCCIONES:
1. Presenta la información biográfica de forma narrativa y fluida
2. Incluye datos personales, trayectoria y afiliación política
3. Describe propuestas y actividades políticas actuales
4. Mantén un tono profesional y objetivo
5. NO uses frases como "se menciona", "no se menciona", "según los documentos"
6. NO hagas referencia a las fuentes o documentos""",
        
        'propuestas_verbo': """
INSTRUCCIONES:
1. Lista todas las propuestas encontradas organizadas por candidato de forma narrativa y fluida
2. Para cada propuesta detalla:
   - Nombre del candidato y partido
   - Detalles específicos
   - Información de implementación
4. NO hagas referencia a documentos o fuentes""",
        
        'entrevista': """
INSTRUCCIONES:
1. De forma narrativa y fluida presenta los temas principales.
2. Dentro de cada tema, usa viñetas para detallar puntos clave.
3. NO hagas referencia a documentos o fuentes explícitas.
4. No menciones que sigues instrucciones ni pongas viñeta en texto""",
        
        'partido_candidato': """
INSTRUCCIONES:
1. Presenta el partido y afiliación política de forma narrativa y fluida
2. Describe historia y trayectoria política
3. NO hagas referencia a documentos o fuentes y no menciones las instrucciones""",
        
        'partido_nombre': """
INSTRUCCIONES:
1. Lista todos los candidatos del partido
2. Para cada uno incluye:
   - Nombre completo
   - Cargo actual
   - Trayectoria relevante
3. NO menciones fuentes de información""",
        
        'propuestas_candidato': """
INSTRUCCIONES:
1. Enumera todas las propuestas principales
2. Organiza por temas o áreas
3. Incluye detalles de implementación
4. NO hagas referencia a documentos"""
    }

    prompt_base += instrucciones.get(tipo, """
INSTRUCCIONES:
1. Resume la información de forma clara y directa
2. Organiza el contenido lógicamente
3. NO hagas referencia a fuentes o documentos""")

    prompt_base += """

REGLAS IMPORTANTES:
1. Escribe de forma fluida y natural
2. Evita completamente referencias a documentos o fuentes
3. NO uses frases como "se menciona" o "según los documentos"
4. Presenta la información de manera directa y objetiva
5. Mantén un tono profesional y claro"""

    return prompt_base

# ------------------------------
# Función para generar una respuesta utilizando un modelo de IA
# ------------------------------
def generar_respuesta_ollama(query, documentos, max_intentos=3):
    """
    Genera una respuesta utilizando un modelo IA basado en la consulta del usuario y los documentos relevantes.
    
    Parámetros:
    query (str): Consulta de búsqueda del usuario.
    documentos (list): Lista de documentos relevantes.
    max_intentos (int): Número máximo de intentos de solicitud al modelo. Por defecto, 3.
    
    Retorna:
    str: Respuesta generada por la IA o mensaje de error.
    """
    if not documentos:
        return "No se encontraron documentos relevantes."

    tipo, param = identificar_tipo_consulta(query)
    prompt = generar_prompt_especifico(tipo, query, documentos)

    for intento in range(max_intentos):
        try:
            session = requests.Session()
            session.timeout = None
            
            respuesta = session.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 1024,
                        "num_thread": 6,   
                        "num_ctx": 4096,
                        "stop": ["</s>"],
                        "repeat_penalty": 1.1
                    }
                }
            )

            if respuesta.status_code == 200:
                texto_respuesta = respuesta.json().get("response", "")
                return texto_respuesta
                
        except Exception as e:
            print(f"\n⚠️ Error en intento {intento + 1}: {str(e)}")
            if intento == max_intentos - 1:
                return generar_respuesta_fallback(tipo, documentos)
    
    return generar_respuesta_fallback(tipo, documentos)


def generar_respuesta_fallback(tipo, documentos):
    respuesta = []
    
    if tipo == "biografia":
        doc_bio = next((doc for doc in documentos if doc['tipo'].lower() == 'biografia'), None)
        if doc_bio:
            respuesta.extend([
                f"📌 Biografía de {doc_bio['presidente']}:",
                f"Partido: {doc_bio['partido']}",
                f"\nInformación biográfica:",
                doc_bio['texto_contexto']
            ])
    
    elif tipo in ["propuestas_verbo", "propuestas_candidato"]:
        respuesta.append("📋 Propuestas encontradas:")
        for doc in documentos:
            respuesta.extend([
                f"\n• Candidato: {doc['presidente']} ({doc['partido']})",
                f"  {doc['texto_contexto']}"
            ])
    
    elif tipo == "entrevista":
        entrevistas = [doc for doc in documentos if doc['tipo'].lower() == 'entrevista']
        for entrevista in entrevistas:
            respuesta.extend([
                f"\n📌 Entrevista con {entrevista['presidente']}:",
                f"Temas tratados: {entrevista.get('tema', 'No especificado')}",
                f"Contenido: {entrevista['texto_contexto']}"
            ])
    
    elif tipo in ["partido_candidato", "partido_nombre"]:
        respuesta.append("🏛️ Información de partido:")
        for doc in documentos:
            respuesta.extend([
                f"\n• {doc['presidente']}",
                f"  Partido: {doc['partido']}",
                f"  {doc['texto_contexto']}"
            ])
    
    return "\n".join(respuesta)

# ----- Endpoints de Flask -----

@app.route('/buscar', methods=['POST'])
def buscar_documentos():
    try:
        datos = request.get_json()
        if not datos:
            return jsonify({"error": "Datos de búsqueda no proporcionados"}), 400

        query = datos.get('query', '')
        if not query:
            return jsonify({"error": "Consulta de búsqueda vacía"}), 400

        k = datos.get('k', 5)
        resultados = buscar(query, k)

        if not resultados:
            return jsonify({"mensaje": "No se encontraron documentos relevantes."}), 404

        # Convertir resultados a tipos JSON serializables
        resultados_serializables = []
        for resultado in resultados:
            resultado_serializable = {}
            for key, value in resultado.items():
                # Convertir numpy tipos a tipos Python estándar
                if isinstance(value, (np.float32, np.float64)):
                    resultado_serializable[key] = float(value)
                elif isinstance(value, np.int32):
                    resultado_serializable[key] = int(value)
                else:
                    resultado_serializable[key] = value
            resultados_serializables.append(resultado_serializable)

        return jsonify(resultados_serializables), 200

    except Exception as e:
        return jsonify({"error": f"Error en la búsqueda: {str(e)}"}), 500

# ------------------------------
# Función para extraer fuentes de los documentos
# ------------------------------
def extraer_fuentes(documentos):
    """
    Extrae las fuentes de los documentos relevantes.
    
    Parámetros:
    documentos (list): Lista de documentos relevantes.
    
    Retorna:
    list: Lista de fuentes identificadas.
    """
    fuentes = []
    for doc in documentos:
        if doc['tipo'] == 'plan':
            # Extraer número de página del ID (formato: lista_pagina_id)
            pagina = doc['id_oracion'].split('_')[1]
            fuentes.append(f"Plan de trabajo de {doc['presidente']}, página {pagina}")
        elif doc['tipo'] == 'entrevista':
            # Mapeo de números a medios
            medios = {
                '1': 'Ecuavisa',
                '2': 'Teleamazonas',
                '3': 'Revista Vistazo'
            }
            num_entrevista = doc['id_oracion'].split('_')[1]
            medio = medios.get(num_entrevista, 'Desconocido')
            fuentes.append(f"Entrevista en {medio} con {doc['presidente']}")
        elif doc['tipo'] == 'biografia':
            fuentes.append("CNN Español y Primicias EC - Perfiles candidatos presidenciales 2025")
    
    return list(set(fuentes))  # Eliminar duplicados


@app.route('/generar_respuesta', methods=['POST'])
def generar_respuesta():
    try:
        datos = request.get_json()
        query = datos.get('query', '')
        k = datos.get('k', 5)

        if not query:
            return jsonify({"error": "Consulta de búsqueda vacía"}), 400

        tipo, param = identificar_tipo_consulta(query)
        query_ajustada = limpiar_query(query, tipo, param)
        
        documentos = buscar(query_ajustada, k)
        
        if not documentos:
            return jsonify({"mensaje": "No se encontraron documentos relevantes."}), 404

        documentos_serializables = []
        for doc in documentos:
            doc_serializable = {}
            for key, value in doc.items():
                if isinstance(value, (np.float32, np.float64)):
                    doc_serializable[key] = float(value)
                else:
                    doc_serializable[key] = value
            documentos_serializables.append(doc_serializable)

        respuesta = generar_respuesta_ollama(query, documentos_serializables)
        fuentes = extraer_fuentes(documentos_serializables)
        
        return jsonify({
            "query_original": query,
            "query_ajustada": query_ajustada,
            "tipo_consulta": tipo,
            "documentos": documentos_serializables,
            "respuesta": respuesta,
            "fuentes": fuentes
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error al generar respuesta: {str(e)}"}), 500

# ----- Ejecutar Aplicación -----

if __name__ == "__main__":
    app.run(port=4000, debug=True)
