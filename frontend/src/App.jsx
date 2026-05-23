import { useCallback, useState } from 'react';
import VapiCall from './components/VapiCall';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const SDR_NAME = 'Sarah Chen';

const TEST_LEAD = {
  lead_name: 'Alex Chen',
  company: 'Acme Corp',
  complaint:
    "Stripe webhooks have been timing out for 3 days, we've lost thousands in failed payments",
};

export default function App() {
  const [callSession, setCallSession] = useState(null);
  const [calling, setCalling] = useState(false);

  const handleCallEnd = useCallback(() => {
    setCallSession(null);
  }, []);

  const startCall = async () => {
    setCalling(true);
    try {
      const res = await fetch(`${API_URL}/call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_name: TEST_LEAD.lead_name,
          company: TEST_LEAD.company,
          complaint: TEST_LEAD.complaint,
          sdr_name: SDR_NAME,
        }),
      });
      const data = await res.json();
      if (data.fallback || data.error || !data.assistant_id) {
        console.log('call error', data.error || 'fallback');
        return;
      }
      setCallSession({
        assistantId: data.assistant_id,
        assistantOverrides: data.assistant_overrides || {},
      });
    } catch (err) {
      console.log('call error', err);
    } finally {
      setCalling(false);
    }
  };

  if (callSession) {
    return (
      <VapiCall
        assistantId={callSession.assistantId}
        assistantOverrides={callSession.assistantOverrides}
        leadName={TEST_LEAD.lead_name}
        company={TEST_LEAD.company}
        sdrName={SDR_NAME}
        onCallEnd={handleCallEnd}
      />
    );
  }

  if (calling) {
    return (
      <div
        style={{
          minHeight: '100vh',
          background: '#0a0a0a',
          color: '#888',
          fontFamily: '"Courier New", Courier, monospace',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '13px',
          letterSpacing: '0.15em',
        }}
      >
        CONNECTING...
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0a0a0a',
        color: '#fff',
        fontFamily: '"Courier New", Courier, monospace',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <p style={{ color: '#555', fontSize: '12px', letterSpacing: '0.2em', marginBottom: '32px' }}>
        RIVAL INTEL — VAPI TEST
      </p>
      <div
        style={{
          background: '#111',
          border: '1px solid #222',
          padding: '24px',
          maxWidth: '420px',
          marginBottom: '32px',
        }}
      >
        <div style={{ fontSize: '18px', marginBottom: '8px' }}>{TEST_LEAD.lead_name}</div>
        <div style={{ fontSize: '12px', color: '#22c55e', marginBottom: '12px' }}>{TEST_LEAD.company}</div>
        <p style={{ fontSize: '13px', color: '#aaa', lineHeight: 1.6, margin: 0 }}>{TEST_LEAD.complaint}</p>
      </div>
      <button
        onClick={startCall}
        disabled={calling}
        style={{
          background: calling ? '#1a1a1a' : '#22c55e',
          color: calling ? '#555' : '#000',
          border: 'none',
          padding: '14px 28px',
          fontFamily: 'inherit',
          fontSize: '13px',
          fontWeight: 'bold',
          letterSpacing: '0.08em',
          cursor: calling ? 'default' : 'pointer',
        }}
      >
        {calling ? 'CONNECTING...' : 'Call Alex Chen'}
      </button>
    </div>
  );
}
