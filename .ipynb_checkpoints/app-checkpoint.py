from flask import Flask, request, jsonify
import re
import pickle
import faiss
import unicodedata
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# ----- Funciones Personalizadas -----

def cargar_sistema():
    try:
        with open('sistema_busqueda.pkl', 'rb') as f:
            data = pickle.load(f)
        data['index'] = faiss.deserialize_index(data['index'])
        return data
    except Exception as e:
        print(f"Error al cargar el sistema: {e}")
        return None

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def es_nombre_presidente(query, presidente):
    query_norm = normalizar_texto(query)
    presidente_norm = normalizar_texto(presidente)
    query_words = set(query_norm.split())
    presidente_words = set(presidente_norm.split())
    palabras_coincidentes = query_words.intersection(presidente_words)
    return query_norm in presidente_norm or presidente_norm in query_norm or len(palabras_coincidentes) >= 2

def calcular_relevancia(query, texto, meta):
    factores = {'palabras_clave': 0, 'exactitud': 0, 'tipo_doc': 0, 'posicion': 0, 'longitud': 0}
    texto_norm = normalizar_texto(texto)
    query_norm = normalizar_texto(query)
    query_words = set(query_norm.split())
    palabras_encontradas = sum(1 for word in query_words if word in texto_norm)
    factores['palabras_clave'] = palabras_encontradas / len(query_words) if query_words else 0

    if query_norm in texto_norm:
        factores['exactitud'] = 1.0

    pesos_tipo = {'plan': 1.3, 'entrevista': 1.2, 'biografia': 1.0}
    peso_base = pesos_tipo.get(meta.get('tipo', ''), 1.0)

    if meta.get('tipo') == 'biografia' and es_nombre_presidente(query, meta.get('presidente', '')):
        peso_base *= 2.5
        factores['exactitud'] = 1.0

    factores['tipo_doc'] = peso_base

    primera_aparicion = min((texto_norm.find(word) for word in query_words if word in texto_norm), default=len(texto_norm))
    factores['posicion'] = 1.0 - (primera_aparicion / len(texto_norm))

    palabras_texto = len(texto.split())
    factores['longitud'] = 1.0 if 10 <= palabras_texto <= 50 else 0.8

    pesos = {'palabras_clave': 0.35, 'exactitud': 0.25, 'tipo_doc': 0.20, 'posicion': 0.15, 'longitud': 0.05}
    puntaje = sum(factor * pesos[nombre] for nombre, factor in factores.items())
    return puntaje

def buscar(query, k=5, umbral_similitud=0.3):
    """Realiza una búsqueda mejorada con mejor ranking"""
    sistema = cargar_sistema()

    # Pre-filtrado con TF-IDF
    query_vec = sistema['vectorizer'].transform([query])
    similitudes = cosine_similarity(query_vec, sistema['tfidf_matrix']).flatten()
    indices_relevantes = np.where(similitudes > umbral_similitud)[0]

    if len(indices_relevantes) == 0:
        return []

    # Búsqueda semántica con FAISS
    model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
    query_embedding = model.encode([query]).astype('float32')
    D, I = sistema['index'].search(query_embedding, k*2)  # Buscamos más resultados para filtrar

    # Preparar resultados con nuevo sistema de ranking
    resultados = []
    for i, (dist, idx) in enumerate(zip(D[0], I[0])):
        if idx < len(sistema['metadata']):
            meta = sistema['metadata'][idx]

            # Calcular relevancia personalizada
            relevancia = calcular_relevancia(
                query,
                meta['texto_original'],
                meta
            )

            # Ajustar distancia por relevancia
            dist_ajustada = dist / (relevancia + 0.1)  # Evitar división por cero

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

    # Ordenar por relevancia y distancia ajustada
    resultados = sorted(resultados,
                       key=lambda x: (-x['relevancia'], x['distancia_ajustada']))

    # Tomar los k mejores resultados
    return resultados[:k]

def mostrar_resultados(query, k=5):
    """Muestra los resultados de búsqueda de manera formateada"""
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

# ----- Ejecutar Aplicación -----

if __name__ == "__main__":
    app.run(port=8080, debug=True)
