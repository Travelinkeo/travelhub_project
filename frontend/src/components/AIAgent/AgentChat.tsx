'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  Fab,
  Collapse,
  CircularProgress,
  Avatar
} from '@mui/material';
import {
  Chat,
  Send,
  Close,
  SmartToy,
  Person
} from '@mui/icons-material';
import { apiMutate } from '@/lib/api';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

export default function AgentChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
    setMessages([{
      id: '1',
      text: '¡Hola! Soy el Agente Inteligente de TravelHub 🤖\n\n¿En qué puedo ayudarte hoy? Puedo ayudarte con:\n• Consultar ventas y estadísticas\n• Revisar cotizaciones pendientes\n• Analizar clientes y pagos\n• Sugerir mejoras para tu negocio',
      isUser: false,
      timestamp: new Date()
    }]);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputMessage,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await apiMutate('/api/ai-agent/chat/', {
        method: 'POST',
        body: JSON.stringify({ message: inputMessage }),
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.response,
        isUser: false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, agentMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta de nuevo.',
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* Chat Window */}
      <Collapse in={isOpen}>
        <Paper
          elevation={8}
          sx={{
            position: 'fixed',
            bottom: 100,
            right: 24,
            width: { xs: 'calc(100vw - 48px)', sm: 400 },
            height: 500,
            display: 'flex',
            flexDirection: 'column',
            zIndex: 1300,
            borderRadius: 2
          }}
        >
          {/* Header */}
          <Box
            sx={{
              p: 2,
              bgcolor: 'primary.main',
              color: 'white',
              borderRadius: '8px 8px 0 0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <Box display="flex" alignItems="center" gap={1}>
              <SmartToy />
              <Typography variant="h6">Agente TravelHub</Typography>
            </Box>
            <IconButton
              size="small"
              onClick={() => setIsOpen(false)}
              sx={{ color: 'white' }}
            >
              <Close />
            </IconButton>
          </Box>

          {/* Messages */}
          <Box
            sx={{
              flex: 1,
              overflow: 'auto',
              p: 1,
              bgcolor: 'grey.50'
            }}
          >
            {messages.map((message) => (
              <Box
                key={message.id}
                sx={{
                  display: 'flex',
                  justifyContent: message.isUser ? 'flex-end' : 'flex-start',
                  mb: 1
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 1,
                    maxWidth: '80%',
                    flexDirection: message.isUser ? 'row-reverse' : 'row'
                  }}
                >
                  <Avatar
                    sx={{
                      width: 32,
                      height: 32,
                      bgcolor: message.isUser ? 'primary.main' : 'secondary.main'
                    }}
                  >
                    {message.isUser ? <Person /> : <SmartToy />}
                  </Avatar>
                  <Paper
                    elevation={1}
                    sx={{
                      p: 1.5,
                      bgcolor: message.isUser ? 'primary.main' : 'white',
                      color: message.isUser ? 'white' : 'text.primary',
                      borderRadius: 2
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}
                    >
                      {message.text}
                    </Typography>
                    {mounted && (
                      <Typography
                        variant="caption"
                        sx={{
                          opacity: 0.7,
                          display: 'block',
                          mt: 0.5
                        }}
                      >
                        {message.timestamp.toLocaleTimeString('es-ES', { hour12: false })}
                      </Typography>
                    )}
                  </Paper>
                </Box>
              </Box>
            ))}
            
            {isLoading && (
              <Box display="flex" justifyContent="flex-start" mb={1}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
                    <SmartToy />
                  </Avatar>
                  <Paper elevation={1} sx={{ p: 1.5, borderRadius: 2 }}>
                    <CircularProgress size={20} />
                  </Paper>
                </Box>
              </Box>
            )}
            
            <div ref={messagesEndRef} />
          </Box>

          {/* Input */}
          <Box
            sx={{
              p: 2,
              borderTop: 1,
              borderColor: 'divider',
              bgcolor: 'white'
            }}
          >
            <Box display="flex" gap={1}>
              <TextField
                fullWidth
                size="small"
                placeholder="Escribe tu mensaje..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                multiline
                maxRows={3}
              />
              <IconButton
                color="primary"
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isLoading}
              >
                <Send />
              </IconButton>
            </Box>
          </Box>
        </Paper>
      </Collapse>

      {/* Floating Action Button */}
      <Fab
        color="primary"
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          zIndex: 1300
        }}
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <Close /> : <Chat />}
      </Fab>
    </>
  );
}