package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
)

const maxRequestBodyBytes = 1 << 20 // 1 MiB

// Server wires the repository and loyalty client to HTTP handlers.
type Server struct {
	repo    *repository
	loyalty *loyaltyClient
}

func NewServer(repo *repository, loyalty *loyaltyClient) *Server {
	return &Server{repo: repo, loyalty: loyalty}
}

// Routes returns a ServeMux with method-qualified patterns (Go 1.22+).
// The mux returns 405 Method Not Allowed automatically for mismatched methods.
func (s *Server) Routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /order", s.handleCreateOrder)
	mux.HandleFunc("GET /order/{id}", s.handleGetOrder)
	return mux
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, healthResponse{OK: true})
}

func (s *Server) handleCreateOrder(w http.ResponseWriter, r *http.Request) {
	// Limit body size to prevent resource exhaustion attacks.
	r.Body = http.MaxBytesReader(w, r.Body, maxRequestBodyBytes)

	var req OrderRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		// Distinguish between a body that exceeded the size limit and one
		// that is simply malformed — they deserve different status codes.
		var maxErr *http.MaxBytesError
		if errors.As(err, &maxErr) {
			http.Error(w, "request body too large", http.StatusRequestEntityTooLarge)
			return
		}
		http.Error(w, "invalid JSON body", http.StatusBadRequest)
		return
	}
	if req.Item == "" {
		http.Error(w, "item is required", http.StatusBadRequest)
		return
	}
	// Reject invalid prices before contacting external services or the DB.
	if req.Price <= 0 {
		http.Error(w, "price must be positive", http.StatusBadRequest)
		return
	}

	points, err := s.loyalty.fetchPoints(req.Item, req.LoyaltyCard)
	if err != nil {
		log.Printf("loyalty service error: %v", err)
		http.Error(w, "loyalty service unavailable", http.StatusServiceUnavailable)
		return
	}

	order, err := s.repo.save(req.Item, req.Price, points)
	if err != nil {
		log.Printf("database save error: %v", err)
		http.Error(w, "database error", http.StatusInternalServerError)
		return
	}

	// 201 Created — ресурс был создан, а не просто обработан запрос.
	writeJSON(w, http.StatusCreated, order)
}

func (s *Server) handleGetOrder(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		http.Error(w, "invalid order id", http.StatusBadRequest)
		return
	}

	order, err := s.repo.findByID(id)
	if errors.Is(err, sql.ErrNoRows) {
		http.Error(w, "order not found", http.StatusNotFound)
		return
	}
	if err != nil {
		log.Printf("database find error: %v", err)
		http.Error(w, "database error", http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusOK, order)
}

// writeJSON serialises v as JSON with the given status code.
// If encoding fails after WriteHeader has been called, the error is only
// logged — headers cannot be retracted at that point.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("writeJSON: encode failed after headers sent: %v", err)
	}
}