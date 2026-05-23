import { useEffect, useRef, useState } from 'react';
import Vapi from '@vapi-ai/web';

export default function VapiCall({
  assistantId,
  assistantOverrides,
  leadName,
  company,
  sdrName,
  onCallEnd,
}) {
  const vapiRef = useRef(null);
  const endedRef = useRef(false);
  const hadErrorRef = useRef(false);
  const onCallEndRef = useRef(onCallEnd);
  const [status, setStatus] = useState('CONNECTING');
  const [speaking, setSpeaking] = useState(false);
  const [transcript, setTranscript] = useState([]);
  const [errorMsg, setErrorMsg] = useState('');

  onCallEndRef.current = onCallEnd;

  useEffect(() => {
    endedRef.current = false;
    hadErrorRef.current = false;
    const publicKey = process.env.REACT_APP_VAPI_PUBLIC_KEY;
    if (!publicKey) {
      setErrorMsg('REACT_APP_VAPI_PUBLIC_KEY not set');
      return undefined;
    }
    if (!assistantId) {
      setErrorMsg('No assistant ID');
      return undefined;
    }

    const vapi = new Vapi(publicKey);
    vapiRef.current = vapi;

    vapi.on('call-start', () => setStatus('LIVE'));
    vapi.on('call-end', () => {
      setStatus('CALL ENDED');
      if (!endedRef.current) {
        endedRef.current = true;
        if (!hadErrorRef.current) {
          onCallEndRef.current();
        }
      }
    });
    vapi.on('speech-start', () => setSpeaking(true));
    vapi.on('speech-end', () => setSpeaking(false));
    vapi.on('error', (err) => {
      console.log('vapi error', err);
      hadErrorRef.current = true;
      const detail =
        err?.error?.message ||
        err?.error?.error?.message ||
        (typeof err?.error === 'string' ? err.error : null) ||
        err?.message;
      setErrorMsg(detail || err?.type || 'Call error');
      setStatus('CALL ENDED');
    });
    vapi.on('message', (msg) => {
      if (msg.type === 'status-update' && msg.status === 'ended') {
        console.log('vapi ended:', msg.endedReason || msg);
      }
      if (msg.type === 'transcript' && msg.transcriptType === 'final') {
        const role = msg.role === 'assistant' ? 'sdr' : 'lead';
        const text = msg.transcript || msg.text || '';
        if (text) {
          setTranscript((prev) => [...prev, { role, text }]);
        }
      }
    });

    vapi.start(assistantId, assistantOverrides || {}).catch((err) => {
      console.log('vapi start error', err);
      setErrorMsg(err?.message || 'Failed to start call');
      setStatus('CALL ENDED');
    });

    // Do not vapi.stop() here — React StrictMode cleanup was killing the call instantly.
    return undefined;
  }, [assistantId, assistantOverrides]);

  const handleEnd = () => {
    endedRef.current = true;
    vapiRef.current?.stop();
    setStatus('CALL ENDED');
    onCallEndRef.current();
  };

  const goBack = () => {
    endedRef.current = true;
    onCallEndRef.current();
  };

  const statusColor =
    status === 'LIVE' ? '#22c55e' : status === 'CONNECTING' ? '#888' : '#ef4444';

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0a0a0a',
        color: '#fff',
        fontFamily: '"Courier New", Courier, monospace',
        padding: '24px',
      }}
    >
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 0.5; }
          50% { transform: scale(1.12); opacity: 1; }
        }
      `}</style>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: '8px',
          fontSize: '12px',
        }}
      >
        <span style={{ color: '#22c55e' }}>{sdrName}</span>
        <span style={{ color: '#888' }}>
          {leadName} · {company}
        </span>
      </div>

      <div
        style={{
          textAlign: 'center',
          fontSize: '11px',
          letterSpacing: '0.2em',
          color: statusColor,
          marginBottom: '16px',
        }}
      >
        {status}
      </div>

      {errorMsg && (
        <p style={{ textAlign: 'center', color: '#ef4444', fontSize: '11px', marginBottom: '24px' }}>
          {errorMsg}
        </p>
      )}

      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          marginBottom: '40px',
        }}
      >
        <div
          style={{
            width: '72px',
            height: '72px',
            borderRadius: '50%',
            background: speaking ? '#22c55e' : '#111',
            border: `2px solid ${speaking ? '#22c55e' : '#333'}`,
            animation: speaking ? 'pulse 1s ease infinite' : 'none',
            transition: 'background 0.2s, border-color 0.2s',
          }}
        />
      </div>

      <div
        style={{
          maxWidth: '560px',
          margin: '0 auto 32px',
          minHeight: '140px',
          background: '#111',
          border: '1px solid #1a1a1a',
          padding: '16px',
        }}
      >
        {transcript.length === 0 && (
          <p style={{ margin: 0, fontSize: '12px', color: '#333' }}>Live transcript...</p>
        )}
        {transcript.map((line, i) => (
          <div key={i} style={{ marginBottom: '10px', fontSize: '12px', lineHeight: 1.5 }}>
            <span style={{ color: line.role === 'sdr' ? '#22c55e' : '#888', marginRight: '8px' }}>
              {line.role === 'sdr' ? 'SDR:' : 'LEAD:'}
            </span>
            <span style={{ color: '#ccc' }}>{line.text}</span>
          </div>
        ))}
      </div>

      <div style={{ textAlign: 'center', display: 'flex', gap: '12px', justifyContent: 'center' }}>
        <button
          onClick={handleEnd}
          style={{
            background: '#ef4444',
            color: '#fff',
            border: 'none',
            padding: '12px 32px',
            fontFamily: 'inherit',
            fontSize: '12px',
            letterSpacing: '0.1em',
            cursor: 'pointer',
          }}
        >
          END CALL
        </button>
        {errorMsg && (
          <button
            onClick={goBack}
            style={{
              background: '#222',
              color: '#fff',
              border: '1px solid #333',
              padding: '12px 24px',
              fontFamily: 'inherit',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            BACK
          </button>
        )}
      </div>
    </div>
  );
}
