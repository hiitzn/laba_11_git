package main

import (
	"database/sql"
)

const schema = `
CREATE TABLE IF NOT EXISTS orders (
	id      INTEGER PRIMARY KEY AUTOINCREMENT,
	item    TEXT    NOT NULL,
	price   REAL    NOT NULL,
	points  INTEGER NOT NULL,
	status  TEXT    NOT NULL
)`

// initDB creates the orders table when it does not already exist.
func initDB(db *sql.DB) error {
	_, err := db.Exec(schema)
	return err
}

// repository handles all persistence operations for orders.
type repository struct {
	db *sql.DB
}

func newRepository(db *sql.DB) *repository {
	return &repository{db: db}
}

// save inserts a completed order and returns it with the auto-generated ID.
func (r *repository) save(item string, price float64, points int) (Order, error) {
	result, err := r.db.Exec(
		"INSERT INTO orders (item, price, points, status) VALUES (?, ?, ?, ?)",
		item, price, points, statusCompleted,
	)
	if err != nil {
		return Order{}, err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return Order{}, err
	}

	return Order{
		ID:     id,
		Item:   item,
		Price:  price,
		Points: points,
		Status: statusCompleted,
	}, nil
}

// findByID returns the order with the given ID, or sql.ErrNoRows when absent.
func (r *repository) findByID(id int64) (Order, error) {
	var o Order
	err := r.db.QueryRow(
		"SELECT id, item, price, points, status FROM orders WHERE id = ?", id,
	).Scan(&o.ID, &o.Item, &o.Price, &o.Points, &o.Status)
	return o, err
}