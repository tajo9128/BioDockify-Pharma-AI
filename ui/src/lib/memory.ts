
export interface MemoryStore {
    shortTerm: any[];
    longTerm: any[];
}

class AgentMemory implements MemoryStore {
    shortTerm: any[] = [];
    longTerm: any[] = [];

    add(item: any) {
        this.shortTerm.push(item);
    }

    clear() {
        this.shortTerm = [];
    }
}

export const memory = new AgentMemory();
