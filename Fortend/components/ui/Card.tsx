import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hoverEffect?: boolean;
}

const Card: React.FC<CardProps> = ({ children, className = '', hoverEffect = false }) => {
  return (
    <div className={`bg-white rounded-xl border border-slate-200 shadow-sm ${hoverEffect ? 'hover:shadow-md transition-shadow duration-300' : ''} ${className}`}>
      {children}
    </div>
  );
};

export default Card;
