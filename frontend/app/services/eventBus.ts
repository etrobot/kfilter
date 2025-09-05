type Callback<T = any> = (payload?: T) => void;

class EventBus {
  private listeners: Map<string, Set<Callback>> = new Map();

  subscribe<T = any>(event: string, cb: Callback<T>) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event)!.add(cb as Callback);
    return () => this.listeners.get(event)!.delete(cb as Callback);
  }

  publish<T = any>(event: string, payload?: T) {
    const set = this.listeners.get(event);
    if (!set) return;
    for (const cb of [...set]) {
      try { (cb as Callback<T>)(payload); } catch (e) { console.error(e); }
    }
  }
}

export const eventBus = new EventBus();
export const subscribe = eventBus.subscribe.bind(eventBus);
export const publish = eventBus.publish.bind(eventBus);

// Common event names
export const EVENTS = {
  ANALYSIS_COMPLETED: 'analysis:completed',
} as const;
