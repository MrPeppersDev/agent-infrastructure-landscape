// See https://svelte.dev/docs/kit/types#app
declare global {
  namespace App {
    // interface Error {}
    // interface Locals {}
    // interface PageData {}
    // interface PageState {}
    // interface Platform {}
  }
}

declare module 'cytoscape-fcose' {
  // Ambient declaration for cytoscape-fcose — the npm package ships JS
  // only (no .d.ts). We use it as `cytoscape.use(fcose)` so the runtime
  // type doesn't matter beyond "this exports something callable".
  const fcose: (cytoscape: unknown) => void;
  export default fcose;
}

export {};
