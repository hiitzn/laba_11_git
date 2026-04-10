package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

const loyaltyTimeout = 5 * time.Second

type loyaltyRequest struct {
	Item        string `json:"item"`
	LoyaltyCard bool   `json:"loyalty_card"`
}

type loyaltyResponse struct {
	Points int `json:"points"`
}

// loyaltyClient calls the Rust loyalty micro-service.
// It owns a dedicated http.Client so timeouts are enforced and connections
// are pooled independently from any global state.
type loyaltyClient struct {
	baseURL    string
	httpClient *http.Client
}

func newLoyaltyClient(baseURL string) *loyaltyClient {
	return &loyaltyClient{
		baseURL:    baseURL,
		httpClient: &http.Client{Timeout: loyaltyTimeout},
	}
}

func (lc *loyaltyClient) fetchPoints(item string, loyaltyCard bool) (int, error) {
	body, err := json.Marshal(loyaltyRequest{Item: item, LoyaltyCard: loyaltyCard})
	if err != nil {
		return 0, fmt.Errorf("marshal loyalty request: %w", err)
	}

	resp, err := lc.httpClient.Post(
		lc.baseURL+"/points",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return 0, fmt.Errorf("call loyalty service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("loyalty service returned HTTP %d", resp.StatusCode)
	}

	var lr loyaltyResponse
	if err := json.NewDecoder(resp.Body).Decode(&lr); err != nil {
		return 0, fmt.Errorf("decode loyalty response: %w", err)
	}
	return lr.Points, nil
}