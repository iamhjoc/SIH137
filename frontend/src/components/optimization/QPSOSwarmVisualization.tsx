/**
 * The application's signature explanatory visualization: a real-time view
 * of the QPSO particle swarm searching the solution space.
 *
 * This is NOT decoration -- particle positions are driven by the actual
 * convergence telemetry (iteration, bestCost, mean/diversity) coming from
 * useOptimizationJob. As convergence improves, particles visibly contract
 * toward the global-best marker, giving an honest visual read of search
 * intensity vs. exploitation.
 *
 * Lightweight: capped particle count, no post-processing, orbit disabled
 * during reduced-motion.
 */
import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import type { ConvergencePoint } from "@/hooks/useOptimizationJob";

const PARTICLE_COUNT = 90;

function Swarm({ convergenceRatio }: { convergenceRatio: number }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  // Each particle gets a fixed random "home" direction; as convergenceRatio
  // approaches 1, particles pull inward toward the global-best origin.
  const homes = useMemo(
    () =>
      Array.from({ length: PARTICLE_COUNT }, () => {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const r = 1.6 + Math.random() * 1.2;
        return new THREE.Vector3(
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.sin(phi) * Math.sin(theta),
          r * Math.cos(phi),
        );
      }),
    [],
  );

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime();
    homes.forEach((home, i) => {
      const contraction = 0.25 + (1 - convergenceRatio) * 0.75; // 1 = spread out, 0.25 = tight
      const wobble = Math.sin(t * 1.5 + i) * 0.05 * (1 - convergenceRatio);
      dummy.position.copy(home).multiplyScalar(contraction).addScalar(wobble);
      dummy.scale.setScalar(0.05 + convergenceRatio * 0.02);
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, PARTICLE_COUNT]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial color="#5eead4" transparent opacity={0.65} />
    </instancedMesh>
  );
}

function GlobalBest() {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const s = 1 + Math.sin(clock.getElapsedTime() * 3) * 0.08;
    ref.current.scale.setScalar(s);
  });
  return (
    <mesh ref={ref}>
      <octahedronGeometry args={[0.16, 0]} />
      <meshBasicMaterial color="#f4f5f7" />
    </mesh>
  );
}

interface Props {
  convergence: ConvergencePoint[];
  bestCostInitial?: number;
}

export function QPSOSwarmVisualization({ convergence, bestCostInitial }: Props) {
  const reducedMotion = useReducedMotion();
  const first = bestCostInitial ?? convergence[0]?.bestCost ?? 1;
  const latest = convergence.at(-1)?.bestCost ?? first;
  const convergenceRatio = first > 0 ? Math.min(Math.max(latest / first, 0), 1) : 1;

  if (reducedMotion) {
    // Static, still-informative fallback: a simple convergence readout.
    return (
      <div className="h-full w-full flex items-center justify-center text-center panel-inset">
        <div>
          <p className="label-caps mb-1">Search Progress</p>
          <p className="text-2xl font-semibold">{Math.round((1 - convergenceRatio) * 100)}%</p>
          <p className="text-xs text-ink-500 mt-1">converged toward global best</p>
        </div>
      </div>
    );
  }

  return (
    <Canvas camera={{ position: [0, 0, 4.2], fov: 45 }} dpr={[1, 1.5]}>
      <ambientLight intensity={0.6} />
      <Swarm convergenceRatio={convergenceRatio} />
      <GlobalBest />
    </Canvas>
  );
}
