import React, { useState, useEffect } from 'react';
import { useMarketStore } from '@/stores/marketStore';

const SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY"];

export default function SymbolSelector() {
  const currentSymbol = useMarketStore(state => state.currentSymbol);
  const setCurrentSymbol = useMarketStore(state => state.setCurrentSymbol);
  
  const [expiries, setExpiries] = useState([]);
  const [selectedExpiry, setSelectedExpiry] = useState(null);

  useEffect(() => {
    fetch(`/api/v1/market/expiries?symbol=${currentSymbol}`)
      .then(async (res) => {
        if (!res.ok) {
          console.warn("Backend not available:", res.status)
          return []
        }

        const text = await res.text()

        try {
          return JSON.parse(text)
        } catch (err) {
          console.warn("Invalid JSON from API:", text)
          return []
        }
      })
      .then((data) => {
        const list =
          data?.expiries ||
          data?.data ||
          data ||
          []

        if (!Array.isArray(list)) {
          setExpiries([])
          return
        }

        setExpiries(list)

        const today = new Date();
        
        const nearest = list
          .map(e => new Date(e))
          .filter(e => e >= today)
          .sort((a: Date, b: Date): number => a.getTime() - b.getTime())[0];

        if (nearest) {
          setSelectedExpiry(
            nearest.toISOString().split("T")[0]
          );
        }
      })
      .catch((err) => {
        console.warn("API request failed:", err)
        setExpiries([])
      });
  }, [currentSymbol]);

  return (
    <div className="flex items-center justify-between w-full">
      <div className="flex gap-3 items-center">
        {SYMBOLS.map(s => (
          <button
            key={s}
            onClick={() => setCurrentSymbol(s)}
            className={s === currentSymbol ? "chip-active" : "chip"}
          >
            {s}
          </button>
        ))}
      </div>
      
      <div className="flex items-center">
        <select
          value={selectedExpiry || ""}
          onChange={(e) => {
            const newExpiry = e.target.value;
            setSelectedExpiry(newExpiry);
            localStorage.setItem("selectedExpiry", newExpiry);
          }}
          style={{minWidth:"140px"}}
          className="
            bg-gray-900
            text-white
            border border-gray-700
            rounded-lg
            px-3 py-1.5
            text-sm
            hover:border-blue-500
            focus:outline-none
          "
        >
          {expiries.map(exp => (
            <option key={exp} value={exp}>
              {exp}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
