package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
)

type errorResponse struct {
	Error string `json:"error"`
}

type Student struct {
	ID    int    `json:"id"`
	Name  string `json:"name"`
	Age   int    `json:"age"`
	Group string `json:"group"`
}

type studentCreateRequest struct {
	Name  string `json:"name"`
	Age   int    `json:"age"`
	Group string `json:"group"`
}

type studentStore struct {
	mu       sync.RWMutex
	students []Student
	nextID   int
}

func newStudentStore() *studentStore {
	return &studentStore{
		nextID: 1,
	}
}

func (s *studentStore) list() []Student {
	s.mu.RLock()
	defer s.mu.RUnlock()

	out := make([]Student, len(s.students))
	copy(out, s.students)
	return out
}

func validateStudentCreateRequest(req studentCreateRequest) error {
	if req.Name == "" {
		return fmt.Errorf("name is required")
	}
	if req.Group == "" {
		return fmt.Errorf("group is required")
	}
	if req.Age <= 0 {
		return fmt.Errorf("age must be positive")
	}
	return nil
}

func (s *studentStore) add(req studentCreateRequest) (Student, error) {
	if err := validateStudentCreateRequest(req); err != nil {
		return Student{}, err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	st := Student{
		ID:    s.nextID,
		Name:  req.Name,
		Age:   req.Age,
		Group: req.Group,
	}
	s.nextID++
	s.students = append(s.students, st)
	return st, nil
}

func writeJSON(w http.ResponseWriter, status int, v any) error {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		return fmt.Errorf("encode JSON response: %w", err)
	}
	return nil
}

func writeJSONAndLog(w http.ResponseWriter, status int, v any, context string) {
	if err := writeJSON(w, status, v); err != nil {
		log.Printf("%s: %v", context, err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSONAndLog(w, status, errorResponse{Error: msg}, "write error response failed")
}

func decodeJSONBody(r *http.Request, dst any) error {
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(dst); err != nil {
		return err
	}
	return nil
}

type studentsAPI struct {
	store *studentStore
}

func newStudentsAPI(store *studentStore) *studentsAPI {
	return &studentsAPI{store: store}
}

func (api *studentsAPI) handleGet(w http.ResponseWriter) {
	writeJSONAndLog(w, http.StatusOK, api.store.list(), "write list response failed")
}

func (api *studentsAPI) handlePost(w http.ResponseWriter, r *http.Request) {
	defer func() {
		if err := r.Body.Close(); err != nil {
			log.Printf("close request body failed: %v", err)
		}
	}()

	var input studentCreateRequest
	if err := decodeJSONBody(r, &input); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}

	created, err := api.store.add(input)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	writeJSONAndLog(w, http.StatusCreated, created, "write create response failed")
}

func (api *studentsAPI) handler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			api.handleGet(w)
		case http.MethodPost:
			api.handlePost(w, r)
		default:
			w.Header().Set("Allow", fmt.Sprintf("%s, %s", http.MethodGet, http.MethodPost))
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	}
}

func newMux(store *studentStore) *http.ServeMux {
	mux := http.NewServeMux()
	api := newStudentsAPI(store)
	mux.HandleFunc("/students", api.handler())
	return mux
}

func main() {
	store := newStudentStore()

	mux := newMux(store)

	addr := ":8080"
	log.Printf("Server is listening on http://localhost%s", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}
