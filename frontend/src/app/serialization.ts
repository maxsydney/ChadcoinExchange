export interface Serializable {
    serialize(): string;
}

export interface Deserializable {
    deserialize(input: any): this;
}
