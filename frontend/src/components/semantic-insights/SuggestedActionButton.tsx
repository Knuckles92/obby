import React, { useState, useRef, useEffect } from 'react';
import { Lightbulb, ChevronRight } from 'lucide-react';

interface SuggestedAction {
    text: string;
    description: string;
}

interface SuggestedActionButtonProps {
    action: SuggestedAction;
    color: string;
    onClick: (action: SuggestedAction, e: React.MouseEvent) => void;
}

export default function SuggestedActionButton({
    action,
    color,
    onClick
}: SuggestedActionButtonProps) {
    const [isHovered, setIsHovered] = useState(false);
    const buttonRef = useRef<HTMLButtonElement>(null);
    const [popupPosition, setPopupPosition] = useState<{ top: number; left: number } | null>(null);

    useEffect(() => {
        if (isHovered && buttonRef.current) {
            const rect = buttonRef.current.getBoundingClientRect();
            // Position popup above the button, centered
            setPopupPosition({
                top: rect.top - 8,
                left: rect.left + rect.width / 2
            });
        }
    }, [isHovered]);

    return (
        <div className="relative inline-block">
            <button
                ref={buttonRef}
                type="button"
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
                onClick={(e) => onClick(action, e)}
                className="group relative flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-200 hover:scale-105 active:scale-95"
                style={{
                    backgroundColor: `${color}15`,
                    color: color,
                    border: `1px solid ${color}30`,
                }}
            >
                <Lightbulb size={12} className="transition-transform group-hover:rotate-12" />
                <span>{action.text}</span>
                <ChevronRight size={10} className="opacity-0 -translate-x-1 transition-all group-hover:opacity-100 group-hover:translate-x-0" />
            </button>

            {isHovered && popupPosition && (
                <div
                    className="fixed z-[100] px-4 py-3 rounded-xl shadow-2xl border pointer-events-none transition-all animate-in fade-in zoom-in duration-200 origin-bottom"
                    style={{
                        top: `${popupPosition.top}px`,
                        left: `${popupPosition.left}px`,
                        transform: 'translate(-50%, -100%)',
                        backgroundColor: 'var(--color-surface)',
                        borderColor: 'var(--color-border)',
                        maxWidth: '280px',
                        width: 'max-content'
                    }}
                >
                    {/* Arrow */}
                    <div
                        className="absolute bottom-[-6px] left-1/2 -translate-x-1/2 w-3 h-3 rotate-45 border-b border-r"
                        style={{
                            backgroundColor: 'var(--color-surface)',
                            borderColor: 'var(--color-border)'
                        }}
                    />

                    <div className="relative">
                        <div className="flex items-center gap-2 mb-1.5">
                            <div
                                className="p-1 rounded-md"
                                style={{ backgroundColor: `${color}20` }}
                            >
                                <Lightbulb size={12} style={{ color: color }} />
                            </div>
                            <span className="font-bold text-[11px] uppercase tracking-wider" style={{ color: color }}>
                                Suggested Action
                            </span>
                        </div>
                        <p className="text-sm font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>
                            {action.text}
                        </p>
                        <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                            {action.description}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
