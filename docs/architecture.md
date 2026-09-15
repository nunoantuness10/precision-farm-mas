# Architecture and design decisions

## Decentralization

`FarmSimulation` is a clock and physical environment, not a decision-making manager.
Sensor agents publish local observations. Each drone owns a sector and independently
announces work. Service agents decide whether to bid from their location, stock, fuel
and the task urgency. The initiating drone awards the contract to the lowest-cost bid.

## Contract Net conversation

1. A drone detects dry soil, weak nutrients, pests or mature crops.
2. It broadcasts a `call-for-proposal` to agents with the matching capability.
3. Feasible agents return proposals containing their local cost.
4. The drone sends one acceptance and rejects the other bids.
5. The contractor consumes resources, changes its zone and reports completion.

Every message contains a performative, sender, recipient, conversation ID, payload and
tick. This makes negotiations inspectable and maps directly to SPADE message metadata.

## SPADE boundary

The core uses an in-memory peer-to-peer bus so the repository runs immediately without
external XMPP credentials. `spade_runtime.py` implements a real SPADE `Agent`, a cyclic
receive behaviour, bidirectional domain-message conversion and asynchronous sending.
`spade-config.example.json` documents the required agent accounts. This separation keeps
decisions testable and lets a deployment replace only the transport layer.

## Metrics

- Yield harvested
- Water, fertilizer and fuel consumed
- Completed and failed tasks
- Messages exchanged
- Contract response time
- Crop health, moisture, nutrients and active-agent count over time
