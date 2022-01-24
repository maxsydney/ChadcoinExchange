import { Serializable, Deserializable } from "../serialization"

export class BuyChadRequest implements Deserializable, Serializable {
    addr: string;
    chadAmount: Number;

    constructor(addr: string, chadAmount: Number) {
        this.addr = addr;
        this.chadAmount = chadAmount;
    }

    deserialize(input: any): this {
        Object.assign(this, input);
        return this;
    }

    serialize(): string {
        return JSON.stringify(this);
    }
}

// export class PriceReturn implements Deserializable, Serializable {
//     price: Number;
//     success: Boolean;

//     constructor(price: Number, success: Boolean) {
//         this.price = price;
//         this.success = success;
//     }

//     deserialize(input: any): this {
//         Object.assign(this, input);
//         return this;
//     }

//     serialize(): string {
//         return JSON.stringify(this); 
//     }
// }

export interface PriceReturn {
    price: Number;
    success: Boolean;
}