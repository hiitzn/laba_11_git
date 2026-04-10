package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	_ "modernc.org/sqlite"
)

// ── Infrastructure ────────────────────────────────────────────────────────────

func newTestServer(t *testing.T, loyaltyURL string) *Server {
    t.Helper()
    if loyaltyURL == "" {
        stub := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
            w.Header().Set("Content-Type", "application/json")
            fmt.Fprintf(w, `{"points":10}`)
        }))
        t.Cleanup(stub.Close)
        loyaltyURL = stub.URL
    }
    db, err := sql.Open("sqlite", ":memory:")
    if err != nil {
        t.Fatalf("open db: %v", err)
    }
    if err := initDB(db); err != nil {
        t.Fatalf("init db: %v", err)
    }
    t.Cleanup(func() { db.Close() })
    return NewServer(newRepository(db), newLoyaltyClient(loyaltyURL))
}

// loyaltyStub returns an httptest.Server that always replies with points.
func loyaltyStub(t *testing.T, points int) *httptest.Server {
	t.Helper()
	stub := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"points":%d}`, points)
	}))
	t.Cleanup(stub.Close)
	return stub
}

// serve dispatches method+path through the production mux so Go 1.22 method
// routing and r.PathValue work exactly as in production.
func serve(t *testing.T, srv *Server, method, path string, body io.Reader) *httptest.ResponseRecorder {
	t.Helper()
	r := httptest.NewRequest(method, path, body)
	if body != nil {
		r.Header.Set("Content-Type", "application/json")
	}
	w := httptest.NewRecorder()
	srv.Routes().ServeHTTP(w, r)
	return w
}

// jsonBody marshals v and returns it as an io.Reader; fatal on error.
func jsonBody(t *testing.T, v any) io.Reader {
	t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatalf("jsonBody: %v", err)
	}
	return bytes.NewReader(b)
}

// decodeJSON deserialises the recorder body into T; fatal on error.
func decodeJSON[T any](t *testing.T, w *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.NewDecoder(w.Body).Decode(&v); err != nil {
		t.Fatalf("decodeJSON: %v (body: %s)", err, w.Body.String())
	}
	return v
}

// assertStatus fails the test when the recorded status differs from want.
func assertStatus(t *testing.T, w *httptest.ResponseRecorder, want int) {
	t.Helper()
	if w.Code != want {
		t.Errorf("status: want %d, got %d (body: %s)", want, w.Code, w.Body.String())
	}
}

// ── GET /health ───────────────────────────────────────────────────────────────

func TestHealth_Returns200WithOkTrue(t *testing.T) {
	srv := newTestServer(t, "")
	w := serve(t, srv, http.MethodGet, "/health", nil)

	assertStatus(t, w, http.StatusOK)
	resp := decodeJSON[healthResponse](t, w)
	if !resp.OK {
		t.Error("health: want ok=true, got false")
	}
}

// ── POST /order ───────────────────────────────────────────────────────────────

func TestCreateOrder_Success(t *testing.T) {
	stub := loyaltyStub(t, 10)

	srv := newTestServer(t, stub.URL)
	w := serve(t, srv, http.MethodPost, "/order",
		jsonBody(t, OrderRequest{Item: "espresso", Price: 2.50}))

	// 201 Created — новый ресурс был создан.
	assertStatus(t, w, http.StatusCreated)
	o := decodeJSON[Order](t, w)

	if o.ID == 0 {
		t.Error("id must not be zero")
	}
	if o.Item != "espresso" {
		t.Errorf("item: want espresso, got %q", o.Item)
	}
	if o.Price != 2.50 {
		t.Errorf("price: want 2.50, got %v", o.Price)
	}
	if o.Points != 10 {
		t.Errorf("points: want 10, got %d", o.Points)
	}
	if o.Status != statusCompleted {
		t.Errorf("status: want %q, got %q", statusCompleted, o.Status)
	}
}

func TestCreateOrder_WithLoyaltyCard(t *testing.T) {
	stub := loyaltyStub(t, 15)

	srv := newTestServer(t, stub.URL)
	w := serve(t, srv, http.MethodPost, "/order",
		jsonBody(t, OrderRequest{Item: "latte", Price: 4.00, LoyaltyCard: true}))

	assertStatus(t, w, http.StatusCreated)
	if got := decodeJSON[Order](t, w).Points; got != 15 {
		t.Errorf("points: want 15, got %d", got)
	}
}

// The handler rejects malformed JSON before contacting the loyalty service,
// so no stub is needed here.
func TestCreateOrder_InvalidJSON_Returns400(t *testing.T) {
	srv := newTestServer(t, "")
	w := serve(t, srv, http.MethodPost, "/order", bytes.NewBufferString("not-json"))

	assertStatus(t, w, http.StatusBadRequest)
	if !strings.Contains(w.Body.String(), "invalid") {
		t.Errorf("want body to mention 'invalid', got: %s", w.Body.String())
	}
}

func TestCreateOrder_OversizedBody_Returns400(t *testing.T) {
	srv := newTestServer(t, "")
	huge := bytes.Repeat([]byte("x"), maxRequestBodyBytes+1)
	w := serve(t, srv, http.MethodPost, "/order", bytes.NewReader(huge))

	assertStatus(t, w, http.StatusBadRequest)
}

func TestCreateOrder_EmptyItem_Returns400(t *testing.T) {
	srv := newTestServer(t, "")
	w := serve(t, srv, http.MethodPost, "/order",
		jsonBody(t, OrderRequest{Item: "", Price: 2.50}))

	assertStatus(t, w, http.StatusBadRequest)
}

func TestCreateOrder_NegativePrice_Returns400(t *testing.T) {
	srv := newTestServer(t, "")
	w := serve(t, srv, http.MethodPost, "/order",
		jsonBody(t, OrderRequest{Item: "espresso", Price: -1.00}))

	assertStatus(t, w, http.StatusBadRequest)
}

func TestCreateOrder_ZeroPrice_Returns400(t *testing.T) {
	srv := newTestServer(t, "")
	w := serve(t, srv, http.MethodPost, "/order",
		jsonBody(t, OrderRequest{Item: "espresso", Price: 0}))

	assertStatus(t, w, http.StatusBadRequest)
}

func TestCreateOrder_LoyaltyServiceDown_Returns503(t *testing.T) {
	srv := newTestServer(t, "http://localhost:0")
	w := serve(t, srv, http.MethodPost, "/order",
		jsonBody(t, OrderRequest{Item: "espresso", Price: 2.50}))

	assertStatus(t, w, http.StatusServiceUnavailable)
}

func TestCreateOrder_WrongMethod_Returns405(t *testing.T) {
	srv := newTestServer(t, "")
	w := serve(t, srv, http.MethodGet, "/order", nil)

	assertStatus(t, w, http.StatusMethodNotAllowed)
}

func TestCreateOrder_ForwardsLoyaltyCardFlag(t *testing.T) {
	var (
		mu       sync.Mutex
		received loyaltyRequest
	)

	stub := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req loyaltyRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "bad payload", http.StatusBadRequest)
			return
		}
		mu.Lock()
		received = req
		mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, `{"points":15}`)
	}))
	t.Cleanup(stub.Close)

	srv := newTestServer(t, stub.URL)
	serve(t, srv, http.MethodPost, "/order",
		jsonBody(t, OrderRequest{Item: "espresso", Price: 2.50, LoyaltyCard: true}))

	mu.Lock()
	loyaltyCard := received.LoyaltyCard
	mu.Unlock()

	if !loyaltyCard {
		t.Error("loyalty_card=true was not forwarded to the loyalty service")
	}
}

// ── GET /order/{id} ──────────────────────────────────────────────────────────

func TestGetOrder_Success(t *testing.T) {
	stub := loyaltyStub(t, 10)

	srv := newTestServer(t, stub.URL)

	pw := serve(t, srv, http.MethodPost, "/order",
		jsonBody(t, OrderRequest{Item: "cappuccino", Price: 3.50}))
	assertStatus(t, pw, http.StatusCreated)
	created := decodeJSON[Order](t, pw)

	gw := serve(t, srv, http.MethodGet, fmt.Sprintf("/order/%d", created.ID), nil)

	assertStatus(t, gw, http.StatusOK)
	fetched := decodeJSON[Order](t, gw)

	if fetched.ID != created.ID {
		t.Errorf("id: want %d, got %d", created.ID, fetched.ID)
	}
	if fetched.Item != "cappuccino" {
		t.Errorf("item: want cappuccino, got %q", fetched.Item)
	}
	if fetched.Status != statusCompleted {
		t.Errorf("status: want %q, got %q", statusCompleted, fetched.Status)
	}
}

func TestGetOrder_NotFound_Returns404(t *testing.T) {
	srv := newTestServer(t, "")
	w := serve(t, srv, http.MethodGet, "/order/9999", nil)

	assertStatus(t, w, http.StatusNotFound)
}

func TestGetOrder_InvalidID_Returns400(t *testing.T) {
	srv := newTestServer(t, "")
	w := serve(t, srv, http.MethodGet, "/order/abc", nil)

	assertStatus(t, w, http.StatusBadRequest)
}

func TestGetOrder_WrongMethod_Returns405(t *testing.T) {
	srv := newTestServer(t, "")
	w := serve(t, srv, http.MethodDelete, "/order/1", nil)

	assertStatus(t, w, http.StatusMethodNotAllowed)
}