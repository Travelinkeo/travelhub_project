'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function ChatbotPage() {
  const { token } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [quickReplies, setQuickReplies] = useState<string[]>([]);
  const [botStatus, setBotStatus] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadBotStatus();
    loadQuickReplies();
    addBotMessage('¡Hola! Soy Linkeo, tu asistente virtual de TravelHub. ¿En qué puedo ayudarte hoy?');
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadBotStatus = async () => {
    if (!token) return;
    try {
      const response = await fetch('http://127.0.0.1:8000/api/chatbot/status/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (data.success) {
        setBotStatus(data);
      }
    } catch (error) {
      console.error('Error loading bot status:', error);
    }
  };

  const loadQuickReplies = async () => {
    if (!token) return;
    try {
      const response = await fetch('http://127.0.0.1:8000/api/chatbot/quick-replies/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (data.success) {
        setQuickReplies(data.quick_replies);
      }
    } catch (error) {
      console.error('Error loading quick replies:', error);
    }
  };

  const addBotMessage = (content: string) => {
    setMessages(prev => [...prev, {
      role: 'assistant',
      content,
      timestamp: new Date()
    }]);
  };

  const sendMessage = async (message: string) => {
    if (!message.trim()) return;
    
    if (!token) {
      addBotMessage('⚠️ Debes iniciar sesión para usar el chatbot.');
      return;
    }

    const userMessage: Message = {
      role: 'user',
      content: message,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chatbot/message/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message,
          conversation_history: messages.map(m => ({
            role: m.role,
            content: m.content
          }))
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        addBotMessage(data.response);
        if (data.quick_replies) {
          setQuickReplies(data.quick_replies);
        }
      } else {
        addBotMessage('Lo siento, hubo un error. Por favor intenta de nuevo.');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      addBotMessage('Error de conexión. Por favor verifica tu conexión a internet.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickReply = (reply: string) => {
    sendMessage(reply);
  };

  const clearChat = () => {
    setMessages([]);
    addBotMessage('¡Hola! Soy Linkeo, tu asistente virtual de TravelHub. ¿En qué puedo ayudarte hoy?');
  };

  return (
    <div className="container mx-auto p-6 h-screen flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <img 
              src="/linkeo-avatar.png" 
              alt="Linkeo" 
              className="w-16 h-16 rounded-full"
            />
            <div>
              <h1 className="text-3xl font-bold">Linkeo</h1>
              <p className="text-gray-600">Asistente Virtual de TravelHub</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {botStatus && (
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${botStatus.status === 'online' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600">{botStatus.status}</span>
              </div>
            )}
            <button
              onClick={clearChat}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Limpiar Chat
            </button>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex-1 bg-white rounded-lg shadow-lg flex flex-col overflow-hidden">
        {/* Mensajes */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <img 
                  src="/linkeo-avatar.png" 
                  alt="Linkeo" 
                  className="w-8 h-8 rounded-full mr-2"
                />
              )}
              <div
                className={`max-w-[70%] p-4 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                <span className="text-xs opacity-70 mt-2 block">
                  {msg.timestamp.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="flex justify-start">
              <img 
                src="/linkeo-avatar.png" 
                alt="Linkeo" 
                className="w-8 h-8 rounded-full mr-2"
              />
              <div className="bg-gray-100 p-4 rounded-lg">
                <div className="flex space-x-2">
                  <div className="w-3 h-3 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-3 h-3 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-3 h-3 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Respuestas rápidas */}
        {quickReplies.length > 0 && !loading && (
          <div className="px-6 py-4 border-t bg-gray-50">
            <p className="text-sm text-gray-600 mb-2">Respuestas rápidas:</p>
            <div className="flex flex-wrap gap-2">
              {quickReplies.map((reply, index) => (
                <button
                  key={index}
                  onClick={() => handleQuickReply(reply)}
                  className="px-4 py-2 text-sm bg-blue-50 text-blue-600 rounded-full hover:bg-blue-100"
                >
                  {reply}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="p-6 border-t">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage(inputMessage);
            }}
            className="flex space-x-4"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Escribe tu mensaje aquí..."
              disabled={loading}
              className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={loading || !inputMessage.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <span>Enviar</span>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}