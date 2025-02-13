import React, { useState, useEffect, useRef } from 'react';
import { Send, Info } from 'lucide-react';
import buhoIcon from './assets/buho.png';
import './App.css';
//import { Send, Info } from 'lucide-react';

// Importar imágenes de candidatos
import lista1 from './assets/lista1.png';
import lista2 from './assets/lista2.png';
import lista3 from './assets/lista3.png';
import lista4 from './assets/lista4.png';
import lista5 from './assets/lista5.png';
import lista6 from './assets/lista6.png';
import lista7 from './assets/lista7.png';
import lista8 from './assets/lista8.png';
import lista12 from './assets/lista12.png';
import lista16 from './assets/lista16.png';
import lista17 from './assets/lista17.png';
import lista18 from './assets/lista18.png';
import lista20 from './assets/lista20.png';
import lista21 from './assets/lista21.png';
import lista23 from './assets/lista23.png';
import lista25 from './assets/lista25.png';



const candidatesInfo = [
  {
    id: 1,
    image: lista1,
    party: "Movimiento Centro Democrático",
    description: "El periodista Jimmy Jairala es el candidato presidencial por el Movimiento Centro Democrático, lista 1. Su compañera de fórmula es la abogada Lucía Vallecilla."
  },
  {
    id: 2,
    image: lista2,
    party: "Partido Unidad Popular",
    description: "El docente Jorge Escala es el candidato presidencial por el Partido Unidad Popular, lista 2. Su compañera de fórmula es la dirigente indígena Pacha Terán."
  },
  {
    id: 3,
    image: lista3,
    party: "Partido Sociedad Patriótica 21 de Enero",
    description: "La ingeniera ambiental Andrea González es la candidata presidencial por el Partido Sociedad patriótica 21 de Enero, lista 3. Su compañero de fórmula es el licenciado en Administración Galo Moncayo."
  },
  {
    id: 4,
    image: lista4,
    party: "Movimiento Pueblo Igualdad Democracia",
    description: "El señor Víctor Araus es el candidato presidencial por el Movimiento Pueblo Igualdad Democracia, lista 4. Su compañera de fórmula es la abogada Cristina Carrera."
  },
  {
    id: 5,
    image: lista5,
    party: "Revolución Ciudadana – RETO",
    description: "La abogada Luisa González es la candidata presidencial por el movimiento Revolución Ciudadana, listas 5-33. Su compañero de fórmula es el economista Diego Borja."
  },
  {
    id: 6,
    image: lista6,
    party: "Partido Social Cristiano",
    description: "El ingeniero mecánico Henry Kronfle, es el candidato presidencial por el Partido Social Cristiano, lista 6. Su compañera de fórmula es la comunicadora Dallyana Passailaigue."
  },
  {
    id: 7,
    image: lista7,
    party: "Movimiento Acción Democrática Nacional, ADN",
    description: "El empresario Daniel Noboa es el candidato por el Movimiento ADN, lista 7. Su compañera de fórmula es la empresaria María José Pinto."
  },
  {
    id: 8,
    image: lista8,
    party: "Partido Avanza",
    description: "El magíster Luis Felipe Tillería es el candidato presidencial por el Partido Avanza, lista 8. Su compañera de fórmula es la ingeniera electrónica Karla Rosero."
  },
  {
    id: 12,
    image: lista12,
    party: "Izquierda Democrática",
    description: "El periodista Carlos Rabascall es el candidato por el partido Izquierda Democrática, lista 12. Su compañera de fórmula es la consultora Alejandra Rivas."
  },
  {
    id: 16,
    image: lista16,
    party: "Movimiento Amigo",
    description: "El ingeniero electrónico Juan Iván Cueva es el candidato presidencial por el Movimiento Amigo, lista 16. Su compañera de fórmula es la abogada Cristina Reyes"
  },
  {
    id: 17,
    image: lista17,
    party: "Partido Socialista Ecuatoriano",
    description: "El abogado Pedro Granja es el candidato presidencial por el Partido Socialista Ecuatoriano, lista 17. Su compañera de fórmula es la académica Verónica Silva."
  },
  {
    id: 18,
    image: lista18,
    party: "Movimiento de Unidad Plurinacional Pachakutik",
    description: "El dirigente indígena Leonidas Iza es el candidato presidencial por el Movimiento Pachakutik, lista 18. Su compañera de fórmula es la activista ambiental Katiuska Molina."
  },
  {
    id: 20,
    image: lista20,
    party: "Movimiento Democracia Sí",
    description: "El abogado Iván Saquicela es el candidato presidencial por el Movimiento Democracia Sí, lista 20. Su compañera de fórmula es la economista María Luisa Coello."
  },
  {
    id: 21,
    image: lista21,
    party: "Movimiento CREO",
    description: "El empresario Francesco Tabacchi es el candidato presidencial por el Movimiento CREO, lista 21. Su compañera de fórmula es la ingeniera comercial Blanca Sacancela."
  },
  {
    id: 23,
    image: lista23,
    party: "SUMA. Partido Sociedad Unida Más Acción",
    description: "El psicólogo Enrique Gómez es el candidato presidencial por el Partido SUMA, lista 23. Su compañera de fórmula es la comunicadora Inés Díaz."
  },
  {
    id: 25,
    image: lista25,
    party: "Movimiento Construye",
    description: "El abogado Henry Cucalón es el candidato presidencial por el Movimiento Construye, lista 25. Su compañera de fórmula es la ingeniera comercial Carla Larrea."
  }
];

function App() {
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const textareaRef = useRef(null);
  const chatBoxRef = useRef(null);

  const [showSourcesIndex, setShowSourcesIndex] = useState(null);
  const handleInputChange = (event) => {
    setInputValue(event.target.value);
    adjustTextareaHeight();
  };

  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 150);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const formatTimestamp = (date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      hour12: true
    }).format(date);
  };

  /*
  const sendMessage = async () => {
    if (inputValue.trim() === '') return;

    const userMessage = {
      sender: 'user',
      text: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      const response = await fetch('http://localhost:4000/generar_respuesta', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userMessage.text, k: 5 }),
      });

      if (!response.ok) {
        throw new Error('Error en la respuesta del servidor');
      }

      const data = await response.json();
      const botResponse = {
        sender: 'bot',
        text: data.respuesta || 'No se encontró una respuesta adecuada.',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botResponse]);
    } catch (error) {
      const errorMessage = {
        sender: 'bot',
        text: 'Lo siento, hubo un error al procesar tu mensaje.',
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  */

  const sendMessage = async () => {
    if (inputValue.trim() === '') return;

    const userMessage = {
      sender: 'user',
      text: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      const response = await fetch('http://localhost:4000/generar_respuesta', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userMessage.text, k: 5 }),
      });

      if (!response.ok) {
        throw new Error('Error en la respuesta del servidor');
      }

      const data = await response.json();
      const botResponse = {
        sender: 'bot',
        text: data.respuesta || 'No se encontró una respuesta adecuada.',
        timestamp: new Date(),
        fuentes: data.fuentes || [] // Añadimos las fuentes a la respuesta del bot
      };

      setMessages(prev => [...prev, botResponse]);
    } catch (error) {
      const errorMessage = {
        sender: 'bot',
        text: 'Lo siento, hubo un error al procesar tu mensaje.',
        timestamp: new Date(),
        isError: true,
        fuentes: [] // Añadimos un array vacío de fuentes para mantener consistencia
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTo({
        top: chatBoxRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages]);

  return (
    <div className="app-container">
      <div className="main-content">
        <div className="chat-interface">
          {/* Header */}
          <div className="chat-header">
            <div className="header-content">
              <div className="bot-info">
                <div className="bot-avatar">
                  <img src={buhoIcon} alt="Bot Icon" className="bot-icon" />
                </div>
                <div className="bot-details">
                  <h1>CandiTrack 2025</h1>
                  <p>AI Assistant</p>
                </div>
              </div>
            </div>
          </div>

          {/* Chat Area */}
          <div className="chat-area" ref={chatBoxRef}>
            {messages.length === 0 ? (
              <div className="welcome-screen">
                <div className="welcome-avatar">
                  <img src={buhoIcon} alt="Bot Icon" className="bot-icon" />
                </div>
                <h2>Welcome to CandiTrack 2025</h2>
                <p>I'm your AI assistant for candidate tracking and analysis. How can I help you today?</p>
              </div>
            ) : (
              <div className="messages-container">

                {/*
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`message-wrapper ${
                      message.sender === 'user' ? 'user-message-wrapper' : 'bot-message-wrapper'
                    }`}
                  >
                    {message.sender === 'bot' && (
                      <div className="bot-avatar message-avatar">
                        <img src={buhoIcon} alt="Bot Icon" className="bot-icon" />
                      </div>
                    )}
                    <div className="message-content">
                      <div className={`message ${
                        message.sender === 'user' ? 'user-message' : 'bot-message'
                      } ${message.isError ? 'error-message' : ''}`}>
                        {message.text}
                      </div>
                      <span className="message-timestamp">
                        {formatTimestamp(message.timestamp)}
                      </span>
                    </div>
                  </div>
                ))}*/}

                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`message-wrapper ${
                      message.sender === 'user' ? 'user-message-wrapper' : 'bot-message-wrapper'
                    }`}
                  >
                    {message.sender === 'bot' && (
                      <div className="bot-avatar message-avatar">
                        <img src={buhoIcon} alt="Bot Icon" className="bot-icon" />
                      </div>
                    )}
                    <div className="message-content">
                      <div className={`message ${
                        message.sender === 'user' ? 'user-message' : 'bot-message'
                      } ${message.isError ? 'error-message' : ''}`}>
                        {message.text}
                        {message.sender === 'bot' && message.fuentes && message.fuentes.length > 0 && (
                          <button 
                            className="sources-button"
                            onClick={() => setShowSourcesIndex(showSourcesIndex === index ? null : index)}
                            title="Ver fuentes"
                          >
                            <Info size={16} />
                          </button>
                        )}
                      </div>
                      {showSourcesIndex === index && message.fuentes && (
                        <div className="sources-popup">
                          <h4>Fuentes:</h4>
                          <ul>
                            {message.fuentes.map((fuente, i) => (
                              <li key={i}>{fuente}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <span className="message-timestamp">
                        {formatTimestamp(message.timestamp)}
                      </span>
                    </div>
                  </div>
                ))}

                {isTyping && (
                  <div className="message-wrapper bot-message-wrapper">
                    <div className="bot-avatar message-avatar">
                      <img src={buhoIcon} alt="Bot Icon" className="bot-icon" />
                    </div>
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="input-area">
            <div className="input-container">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Message CandiTrack 2025..."
                className="message-input"
              />
              <button
                onClick={sendMessage}
                disabled={inputValue.trim() === ''}
                className={`send-button ${inputValue.trim() === '' ? 'disabled' : ''}`}
              >
                <Send className="send-icon" />
              </button>
            </div>
          </div>
        </div>

        {/* Candidates Gallery */}
        <div className="candidates-gallery">
          <div className="candidates-container">
            <div className="candidates-grid">
              {candidatesInfo.map((candidate) => (
                <div key={candidate.id} className="candidate-item">
                  <img src={candidate.image} alt={`Candidato Lista ${candidate.id}`} />
                  <div className="candidate-info">
                    <div className="info-content">
                      <div className="candidate-number">Lista {candidate.id}</div>
                      <h3>{candidate.party}</h3>
                      <p>{candidate.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;