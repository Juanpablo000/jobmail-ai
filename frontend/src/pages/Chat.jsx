import React, { useState, useRef, useEffect } from 'react';

const DEFAULT_WELCOME = {
  role: 'assistant',
  content:
    '¡Hola! Soy tu asistente de empleo en JobMail AI. Consulto directamente las ofertas almacenadas en tu base de datos.\n\nPuedes preguntarme cosas como:\n• "¿Qué ofertas hay de trainee o junior en analítica de datos?"\n• "¿Cuáles son las ofertas remotas disponibles?"\n• "¿Qué vacantes tienen salario especificado superior a 3 millones?"',
};

export default function Chat() {
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem('jobmail_chat_history');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    return [DEFAULT_WELCOME];
  });

  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streaming]);

  useEffect(() => {
    try {
      localStorage.setItem('jobmail_chat_history', JSON.stringify(messages));
    } catch {}
  }, [messages]);

  const handleClearHistory = () => {
    if (window.confirm('¿Deseas reiniciar la conversación con el asistente?')) {
      setMessages([DEFAULT_WELCOME]);
      try {
        localStorage.removeItem('jobmail_chat_history');
      } catch {}
    }
  };

  const handleSend = async (textToSend = input) => {
    const query = textToSend.trim();
    if (!query || streaming) return;

    const userMessage = { role: 'user', content: query };
    const newHistory = [...messages, userMessage];

    setMessages(newHistory);
    setInput('');
    setStreaming(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          history: newHistory.slice(-6),
        }),
      });

      if (!response.ok) {
        throw new Error(`Error del servidor (${response.statusText})`);
      }

      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let accumulated = '';

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.replace('data: ', '');
              if (data === '[DONE]') {
                done = true;
                break;
              }
              accumulated += data;
              setMessages((prev) => {
                const next = [...prev];
                next[next.length - 1] = {
                  role: 'assistant',
                  content: accumulated,
                };
                return next;
              });
            }
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Error contactando al agente: ${err.message}. Asegúrate de tener LM Studio abierto con el modelo cargado y el servidor local en el puerto 1234.`,
        },
      ]);
    } finally {
      setStreaming(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestions = [
    'Ofertas de trainee en analítica de datos',
    'Vacantes remotas con salario indicado',
    'Ofertas en Medellín y Antioquia',
    'Puestos para desarrollador Python o Data',
  ];

  return (
    <div style={styles.container}>
      <div style={styles.chatBox}>
        <header style={styles.header}>
          <div>
            <h2 style={styles.title}>Asistente de Empleo</h2>
            <p style={styles.subtitle}>
              Motor RAG local conectado a LM Studio (<code>ibm/granite-4-h-tiny</code>)
            </p>
          </div>

          <button
            onClick={handleClearHistory}
            style={styles.clearBtn}
            title="Borrar historial y comenzar nueva conversación"
          >
            🧹 Limpiar chat
          </button>
        </header>

        <div style={styles.messagesContainer}>
          {messages.map((msg, index) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={index}
                style={{
                  ...styles.messageRow,
                  justifyContent: isUser ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    ...styles.messageBubble,
                    backgroundColor: isUser ? '#0284c7' : 'var(--bg-card)',
                    color: isUser ? '#ffffff' : 'var(--text-main)',
                    border: isUser ? 'none' : '1px solid var(--border-color)',
                  }}
                >
                  <div style={styles.roleLabel(isUser)}>
                    {isUser ? 'Tú' : 'JobMail Assistant'}
                  </div>
                  <div style={styles.messageContent}>
                    {msg.content}
                  </div>
                </div>
              </div>
            );
          })}
          {streaming && (
            <div style={styles.streamingIndicator}>
              <span style={styles.pulseDot} />
              <span>Generando respuesta en tiempo real...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={styles.suggestionsRow}>
          {suggestions.map((sug, i) => (
            <button
              key={i}
              onClick={() => handleSend(sug)}
              disabled={streaming}
              style={styles.suggestionBtn}
            >
              💡 {sug}
            </button>
          ))}
        </div>

        <footer style={styles.inputArea}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Pregunta por vacantes, salarios, tecnologías o ciudades... (Enter para enviar, Shift+Enter para nueva línea)"
            rows={2}
            style={styles.textarea}
            disabled={streaming}
          />
          <button
            onClick={() => handleSend()}
            disabled={streaming || !input.trim()}
            style={{
              ...styles.sendBtn,
              opacity: streaming || !input.trim() ? 0.45 : 1,
              cursor: streaming || !input.trim() ? 'not-allowed' : 'pointer',
            }}
          >
            {streaming ? '⏳' : 'Enviar 🚀'}
          </button>
        </footer>
      </div>
    </div>
  );
}

const styles = {
  container: {
    maxWidth: '1080px',
    margin: '0 auto',
    padding: '1.25rem 1.5rem',
    height: 'calc(100vh - 85px)',
    display: 'flex',
    flexDirection: 'column',
  },
  chatBox: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '14px',
    border: '1px solid var(--border-color)',
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
    boxShadow: '0 8px 20px rgba(0, 0, 0, 0.35)',
  },
  header: {
    padding: '1rem 1.5rem',
    backgroundColor: 'var(--bg-primary)',
    borderBottom: '1px solid var(--border-color)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: '1.2rem',
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: '-0.01em',
  },
  subtitle: {
    fontSize: '0.8rem',
    color: 'var(--text-muted)',
    marginTop: '0.15rem',
  },
  clearBtn: {
    backgroundColor: 'transparent',
    border: '1px solid var(--border-color)',
    color: 'var(--text-muted)',
    padding: '0.4rem 0.85rem',
    fontSize: '0.8rem',
    fontWeight: '500',
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '1.5rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  messageRow: {
    display: 'flex',
    width: '100%',
  },
  messageBubble: {
    maxWidth: '78%',
    padding: '0.95rem 1.25rem',
    borderRadius: '12px',
    boxShadow: '0 2px 5px rgba(0,0,0,0.15)',
  },
  roleLabel: (isUser) => ({
    fontSize: '0.7rem',
    fontWeight: '700',
    opacity: isUser ? 0.85 : 0.6,
    marginBottom: '0.35rem',
    letterSpacing: '0.04em',
  }),
  messageContent: {
    fontSize: '0.92rem',
    whiteSpace: 'pre-wrap',
    lineHeight: '1.55',
  },
  streamingIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.82rem',
    color: 'var(--accent)',
    padding: '0.25rem 0.5rem',
  },
  pulseDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: 'var(--accent)',
  },
  suggestionsRow: {
    display: 'flex',
    gap: '0.5rem',
    padding: '0.65rem 1.25rem',
    overflowX: 'auto',
    backgroundColor: 'var(--bg-primary)',
    borderTop: '1px solid var(--border-color)',
  },
  suggestionBtn: {
    backgroundColor: 'var(--bg-card)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border-color)',
    padding: '0.4rem 0.8rem',
    fontSize: '0.8rem',
    whiteSpace: 'nowrap',
    borderRadius: '6px',
  },
  inputArea: {
    display: 'flex',
    gap: '0.75rem',
    padding: '1rem 1.25rem',
    backgroundColor: 'var(--bg-primary)',
    borderTop: '1px solid var(--border-color)',
  },
  textarea: {
    flex: 1,
    backgroundColor: 'var(--bg-card)',
    border: '1px solid var(--border-color)',
    color: '#ffffff',
    borderRadius: '8px',
    padding: '0.75rem 1rem',
    fontSize: '0.9rem',
    resize: 'none',
    outline: 'none',
  },
  sendBtn: {
    backgroundColor: 'var(--accent)',
    color: '#090e1a',
    fontWeight: '700',
    padding: '0 1.35rem',
    fontSize: '0.9rem',
    borderRadius: '8px',
  },
};
