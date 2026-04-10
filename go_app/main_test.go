package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestStudentStoreAdd_ValidStudent(t *testing.T) {
	store := newStudentStore()

	created, err := store.add(studentCreateRequest{Name: "Alice", Age: 20, Group: "A1"})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if created.ID != 1 {
		t.Fatalf("expected ID=1, got %d", created.ID)
	}
	if created.Name != "Alice" || created.Age != 20 || created.Group != "A1" {
		t.Fatalf("unexpected created student: %+v", created)
	}

	list := store.list()
	if len(list) != 1 {
		t.Fatalf("expected 1 student in list, got %d", len(list))
	}
	if list[0].ID != 1 {
		t.Fatalf("expected list[0].ID=1, got %d", list[0].ID)
	}
}

func TestStudentStoreAdd_InvalidStudent(t *testing.T) {
	store := newStudentStore()

	tests := []struct {
		name    string
		input   studentCreateRequest
		wantErr bool
	}{
		{name: "missing name", input: studentCreateRequest{Age: 20, Group: "A1"}, wantErr: true},
		{name: "missing group", input: studentCreateRequest{Name: "Bob", Age: 20}, wantErr: true},
		{name: "non-positive age", input: studentCreateRequest{Name: "Bob", Age: 0, Group: "A1"}, wantErr: true},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			_, err := store.add(tc.input)
			if tc.wantErr && err == nil {
				t.Fatalf("expected error, got nil")
			}
			if !tc.wantErr && err != nil {
				t.Fatalf("expected nil error, got %v", err)
			}
		})
	}
}

func TestStudentsHandlerGet_ReturnsEmptyList(t *testing.T) {
	store := newStudentStore()
	server := httptest.NewServer(newMux(store))
	t.Cleanup(server.Close)

	resp, err := http.Get(server.URL + "/students")
	if err != nil {
		t.Fatalf("GET request failed: %v", err)
	}
	t.Cleanup(func() { _ = resp.Body.Close() })

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected status 200, got %d", resp.StatusCode)
	}

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body failed: %v", err)
	}

	var got []Student
	if err := json.Unmarshal(bodyBytes, &got); err != nil {
		t.Fatalf("unmarshal response failed: %v; body=%s", err, string(bodyBytes))
	}
	if len(got) != 0 {
		t.Fatalf("expected empty list, got %d items", len(got))
	}
}

func TestStudentsHandlerPost_CreatesStudent(t *testing.T) {
	store := newStudentStore()
	server := httptest.NewServer(newMux(store))
	t.Cleanup(server.Close)

	payload := []byte(`{"name":"Alice","age":21,"group":"G1"}`)
	resp, err := http.Post(server.URL+"/students", "application/json", bytes.NewReader(payload))
	if err != nil {
		t.Fatalf("POST request failed: %v", err)
	}
	t.Cleanup(func() { _ = resp.Body.Close() })

	if resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		t.Fatalf("expected status 201, got %d; body=%s", resp.StatusCode, string(body))
	}

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body failed: %v", err)
	}

	var created Student
	if err := json.Unmarshal(bodyBytes, &created); err != nil {
		t.Fatalf("unmarshal response failed: %v; body=%s", err, string(bodyBytes))
	}
	if created.ID != 1 || created.Name != "Alice" || created.Age != 21 || created.Group != "G1" {
		t.Fatalf("unexpected created student: %+v", created)
	}
}

func TestStudentsHandlerPost_InvalidJSON_Returns400(t *testing.T) {
	store := newStudentStore()
	req := httptest.NewRequest(http.MethodPost, "/students", bytes.NewBufferString("{bad json"))
	rec := httptest.NewRecorder()

	newStudentsAPI(store).handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected status 400, got %d", rec.Code)
	}
}

func TestStudentsHandlerPost_UnknownField_Returns400(t *testing.T) {
	store := newStudentStore()
	req := httptest.NewRequest(http.MethodPost, "/students", bytes.NewBufferString(`{"name":"Alice","age":21,"group":"G1","extra":1}`))
	rec := httptest.NewRecorder()

	newStudentsAPI(store).handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected status 400, got %d", rec.Code)
	}
}

func TestStudentsHandlerPost_ValidationError_Returns400(t *testing.T) {
	store := newStudentStore()
	req := httptest.NewRequest(http.MethodPost, "/students", bytes.NewBufferString(`{"name":"","age":21,"group":"G1"}`))
	rec := httptest.NewRecorder()

	newStudentsAPI(store).handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected status 400, got %d", rec.Code)
	}
}

func TestStudentsHandlerUnsupportedMethod_Returns405AndAllowHeader(t *testing.T) {
	store := newStudentStore()
	req := httptest.NewRequest(http.MethodPut, "/students", nil)
	rec := httptest.NewRecorder()

	newStudentsAPI(store).handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected status 405, got %d", rec.Code)
	}
	allow := rec.Header().Get("Allow")
	if allow == "" {
		t.Fatalf("expected Allow header to be set")
	}
}
