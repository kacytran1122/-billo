"use client";

import {
  useEffect,
  useRef,
  useState,
  type ComponentPropsWithoutRef,
} from "react";

import styles from "./LazySection.module.css";

type LazySectionProps = ComponentPropsWithoutRef<"section"> & {
  placeholderCards?: number;
  placeholderHeight?: number;
};

/** Mounts expensive section content shortly before it reaches the viewport. */
export function LazySection({
  children,
  placeholderCards = 3,
  placeholderHeight = 520,
  ...sectionProps
}: LazySectionProps) {
  const sectionRef = useRef<HTMLElement>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;
    if (!("IntersectionObserver" in window)) {
      setLoaded(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        setLoaded(true);
        observer.disconnect();
      },
      { rootMargin: "500px 0px", threshold: 0.01 },
    );

    observer.observe(section);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} aria-busy={!loaded} {...sectionProps}>
      {loaded ? (
        <div className={styles.content}>{children}</div>
      ) : (
        <div
          className={styles.skeleton}
          style={{ minHeight: `${placeholderHeight}px` }}
          role="status"
          aria-label="Loading section"
        >
          <span className={styles.heading} />
          <span className={styles.subheading} />
          <div className={styles.cards}>
            {Array.from({ length: placeholderCards }, (_, index) => (
              <span className={styles.card} key={index} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
