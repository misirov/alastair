#[starknet::interface]
pub trait INPC<TContractState> {
    // Change state
    fn change_mood(ref self: TContractState, new_mood: felt252);
    // Read state
    fn get_mood(self: @TContractState) -> felt252;
}

#[starknet::contract]
mod NPC {

    #[storage]
    struct Storage {
        mood: felt252
    }

    #[abi(embed_v0)]
    impl NPC of super::INPC<ContractState> {
        fn change_mood(ref self: ContractState, new_mood: felt252) {
            self.mood.write(new_mood);
        }

        fn get_mood(self: @ContractState) -> felt252 {
            return self.mood.read();
        }
    }


}

