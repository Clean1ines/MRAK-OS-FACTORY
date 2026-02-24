// frontend/src/components/ios/IOSShell.tsx
import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export const IOSShell = ({ children }: { children: React.ReactNode }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Three.js фон (из прототипа)
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      1,
      2000
    );
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    containerRef.current.appendChild(renderer.domElement);

    const geo = new THREE.BufferGeometry();
    const pos = [];
    for (let i = 0; i < 3000; i++) {
      pos.push(
        THREE.MathUtils.randFloatSpread(2000),
        THREE.MathUtils.randFloatSpread(2000),
        THREE.MathUtils.randFloatSpread(2000)
      );
    }
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));

    const mat = new THREE.PointsMaterial({
      color: 0xb8956a,
      size: 1.5,
      transparent: true,
      opacity: 0.35,
      sizeAttenuation: true,
    });
    const cloud = new THREE.Points(geo, mat);
    scene.add(cloud);
    camera.position.z = 800;

    const anim = () => {
      requestAnimationFrame(anim);
      cloud.rotation.y += 0.0003;
      cloud.rotation.x += 0.0001;
      renderer.render(scene, camera);
    };
    anim();

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      containerRef.current?.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  return (
    <div className="relative h-screen w-screen overflow-hidden font-mono">
      <div ref={containerRef} id="three-container" className="absolute inset-0 z-0" />
      <div className="relative z-10 h-full flex flex-col">{children}</div>
    </div>
  );
};