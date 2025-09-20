'use client';

import { useState } from 'react';

type Message = {
  id: number;
  text: string;
  sender: 'user' | 'bot';
};

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem('message') as HTMLInputElement;
    const query = input.value.trim();
    if (!query) return;

    // Add user message to chat
    setMessages((prev) => [...prev, { id: Date.now(), text: query, sender: 'user' }]);
    input.value = '';
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('query', query);

      const res = await fetch('http://localhost:8000/asistente/', {
        method: 'POST',
        body: new URLSearchParams(formData as any),
      });

      if (!res.ok) {
        throw new Error(`Error del servidor: ${res.status}`);
      }

      const data = await res.json();
      // Add bot response to chat
      setMessages((prev) => [...prev, { id: Date.now() + 1, text: data.answer, sender: 'bot' }]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, text: `Error: ${err.message}`, sender: 'bot' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Chat Window */}
      <div className={`fixed bottom-24 right-6 w-96 bg-white rounded-lg shadow-xl transition-transform duration-300 ${isOpen ? 'transform-none' : 'transform-translate-y-full opacity-0'}`}>
        <div className="p-4 bg-brand-primary text-brand-on-primary rounded-t-lg">
          <h3 className="font-bold text-lg">Asistente de Contabilidad</h3>
        </div>
        <div className="p-4 h-80 overflow-y-auto">
          {messages.map((msg) => (
            <div key={msg.id} className={`my-2 p-3 rounded-lg max-w-xs ${msg.sender === 'user' ? 'bg-blue-100 ml-auto' : 'bg-gray-100'}`}>
              <pre className="whitespace-pre-wrap text-sm">{msg.text}</pre>
            </div>
          ))}
          {loading && <div className="my-2 p-3 rounded-lg max-w-xs bg-gray-100">...</div>}
        </div>
        <form onSubmit={handleSubmit} className="p-4 border-t">
          <input
            type="text"
            name="message"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Escribe tu pregunta..."
          />
        </form>
      </div>

      {/* Floating Action Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 w-16 h-16 bg-brand-accent text-brand-on-accent rounded-full shadow-lg flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-accent"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          {isOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          )}
        </svg>
      </button>
    </>
  );
};

export default Chatbot;
