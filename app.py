import React, { useState } from 'react';
import { Delete, Equal, Calculator as CalcIcon } from 'lucide-react';

export default function App() {
 
      setIsNewNumber(true);
    } catch

  const toggleSign = () => {
    setDisplay(String(parseFloat(display) * -1));
  };

  const Button = ({ text, onClick, variant = 'default', className = '' }) => {
    const baseStyle = "h-16 w-16 rounded-2xl text-xl font-semibold transition-all duration-200 active:scale-95 flex items-center justify-center shadow-sm";
    
    const variants = {
      default: "bg-white text-gray-700 hover:bg-gray-50 border border-gray-100",
      primary: "bg-indigo-600 text-white hover:bg-indigo-700 shadow-indigo-200",
      secondary: "bg-gray-100 text-gray-600 hover:bg-gray-200",
      accent: "bg-orange-500 text-white hover:bg-orange-600 shadow-orange-200"
    };

    return (
      <button 
        onClick={onClick}
        className={`${baseStyle} ${variants[variant]} ${className}`}
      >
        {text}
      </button>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 font-sans">
      <div className="bg-white p-6 rounded-3xl shadow-xl w-full max-w-sm border border-gray-100">
        
        {/* Header */}
        <div className="flex items-center gap-2 mb-6 text-indigo-600 opacity-80">
          <CalcIcon size={20} />
          <span className="text-sm font-medium tracking-wide">Simple Calc</span>
        </div>

        {/* Display */}
        <div className="bg-gray-900 rounded-2xl p-6 mb-6 text-right shadow-inner">
          <div className="text-gray-400 text-sm h-6 font-mono mb-1 overflow-hidden">
            {equation}
          </div>
          <div className="text-white text-4xl font-light tracking-wider overflow-hidden">
            {display}
          </div>
        </div>

        {/* Keypad */}
        <div className="grid grid-cols-4 gap-3">
          <Button text="C" onClick={clear} variant="secondary" className="text-red-500" />
          <Button text="+/-" onClick={toggleSign} variant="secondary" />
          <Button text="%" onClick={percentage} variant="secondary" />
          <Button text="÷" onClick={() => handleOperator('/')} variant="accent" />

          <Button text="7" onClick={() => handleNumber(7)} />
          <Button text="8" onClick={() => handleNumber(8)} />
          <Button text="9" onClick={() => handleNumber(9)} />
          <Button text="×" onClick={() => handleOperator('*')} variant="accent" />

          <Button text="4" onClick={() => handleNumber(4)} />
          <Button text="5" onClick={() => handleNumber(5)} />
          <Button text="6" onClick={() => handleNumber(6)} />
          <Button text="-" onClick={() => handleOperator('-')} variant="accent" />

          <Button text="1" onClick={() => handleNumber(1)} />
          <Button text="2" onClick={() => handleNumber(2)} />
          <Button text="3" onClick={() => handleNumber(3)} />
          <Button text="+" onClick={() => handleOperator('+')} variant="accent" />

          <Button text="0" onClick={() => handleNumber(0)} className="col-span-2 w-full" />
          <Button text="." onClick={() => handleNumber('.')} />
          <Button text={<Equal size={24} />} onClick={calculate} variant="primary" />
        </div>
      </div>
    </div>
  );
}
