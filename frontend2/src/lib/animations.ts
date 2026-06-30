import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

// Register ScrollTrigger globally once
gsap.registerPlugin(ScrollTrigger);

/**
 * Initializes generic scroll animations across the site.
 * Call this inside a useGSAP hook to ensure proper React cleanup.
 */
export const initScrollAnimations = (scope?: string | HTMLElement) => {
  const targetScope = typeof scope === 'string' ? document.querySelector(scope) : scope;
  // Elements with .animate-fade-up will gently fade and slide up as they enter viewport
  const elements = gsap.utils.toArray<HTMLElement>('.animate-fade-up', targetScope || undefined);
  
  elements.forEach((el) => {
    gsap.fromTo(
      el,
      { y: 30, opacity: 0 },
      {
        y: 0,
        opacity: 1,
        duration: 0.6,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: el,
          start: 'top 85%',
          // toggleActions: "play none none none", // default is play once
        },
      }
    );
  });
};

/**
 * Animates the entrance of hero section elements sequentially.
 * Best paired with elements tagged with the .hero-element class.
 */
export const animateHeroEntrance = (scope?: string | HTMLElement) => {
  const targetScope = typeof scope === 'string' ? document.querySelector(scope) : scope;
  const elements = gsap.utils.toArray<HTMLElement>('.hero-element', targetScope || undefined);
  if (elements.length === 0) return;

  const tl = gsap.timeline();
  tl.fromTo(
    elements,
    { y: 20, opacity: 0 },
    {
      y: 0,
      opacity: 1,
      duration: 0.7,
      stagger: 0.1,
      ease: 'power3.out',
    }
  );
  return tl;
};

/**
 * Subtle hover animations for buttons/cards via JS (if CSS isn't enough).
 * Use this sparingly, CSS transitions are usually preferred for simple hovers.
 */
export const initHoverEffects = (scope?: string | HTMLElement) => {
  const targetScope = typeof scope === 'string' ? document.querySelector(scope) : scope;
  const elements = gsap.utils.toArray<HTMLElement>('.animate-hover', targetScope || undefined);
  elements.forEach((el) => {
    el.addEventListener('mouseenter', () => {
      gsap.to(el, { scale: 1.02, duration: 0.3, ease: 'power2.out' });
    });
    el.addEventListener('mouseleave', () => {
      gsap.to(el, { scale: 1, duration: 0.3, ease: 'power2.out' });
    });
  });
};
