package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"

	_ "modernc.org/sqlite"
)

func main() {
	loyaltyURL := lookupEnv("LOYALTY_URL", "http://localhost:8081")
	dbPath := lookupEnv("DB_PATH", "./orders.db")
	addr := ":" + lookupEnv("PORT", "8080")

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	// G6: defer db.Close() will not execute when log.Fatalf below calls
	// os.Exit, but that is acceptable — the process is terminating anyway.
	defer db.Close()

	if err := initDB(db); err != nil {
		log.Fatalf("initialise database: %v", err)
	}

	srv := NewServer(newRepository(db), newLoyaltyClient(loyaltyURL))

	log.Printf("order service listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, srv.Routes()))
}

// lookupEnv returns the value of key if it is set and non-empty,
// otherwise it returns fallback. os.LookupEnv is used rather than
// os.Getenv so that an explicitly empty variable ("") is treated the
// same as an unset one — both fall back to the default.
func lookupEnv(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return fallback
}