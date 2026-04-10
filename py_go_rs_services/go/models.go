package main

// statusCompleted is the only terminal status an order can reach.
const statusCompleted = "completed"

// OrderRequest is the payload accepted from the Python gateway.
type OrderRequest struct {
	Item        string  `json:"item"`
	Price       float64 `json:"price"`
	LoyaltyCard bool    `json:"loyalty_card"`
}

// Order is the canonical domain object persisted in SQLite and returned to callers.
type Order struct {
	ID     int64   `json:"id"`
	Item   string  `json:"item"`
	Price  float64 `json:"price"`
	Points int     `json:"points"`
	Status string  `json:"status"`
}

// healthResponse is the wire-format for GET /health.
// Using a named struct instead of map[string]bool documents the contract.
type healthResponse struct {
	OK bool `json:"ok"`
}