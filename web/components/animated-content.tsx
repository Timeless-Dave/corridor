"use client";
// Reduced mount-only adaptation of React Bits AnimatedContent. See SOURCES.md.
import { useLayoutEffect, useRef, type ReactNode } from "react";
import { gsap } from "gsap";
export function AnimatedContent({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ref.current,
        { opacity: 0, y: 10 },
        {
          opacity: 1,
          y: 0,
          duration: 0.32,
          ease: "power2.out",
          clearProps: "transform",
        },
      );
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
