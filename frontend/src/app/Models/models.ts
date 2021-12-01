import { Serializable, Deserializable } from "../serialization"

export class BuyChadRequest implements Deserializable, Serializable {
    addr: string;
    algoAmount: Number;

    constructor(addr: string, algoAmount: Number) {
        this.addr = addr;
        this.algoAmount = algoAmount;
    }

    deserialize(input: any): this {
        Object.assign(this, input);
        return this;
    }

    serialize(): string {
        return JSON.stringify(this); 
    }
}