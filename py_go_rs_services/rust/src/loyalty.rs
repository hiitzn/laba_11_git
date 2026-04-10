//! Pure domain logic for the loyalty points system.
//! No HTTP, no I/O — trivially unit-testable.

pub const BASE_POINTS: u32 = 10;
pub const LOYALTY_BONUS: u32 = 5;

/// Calculate loyalty points for one order.
///
/// Every drink earns [`BASE_POINTS`].
/// Presenting a loyalty card adds [`LOYALTY_BONUS`] on top.
pub fn calculate_points(loyalty_card: bool) -> u32 {
    BASE_POINTS + if loyalty_card { LOYALTY_BONUS } else { 0 }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn no_card_earns_base_points() {
        assert_eq!(calculate_points(false), BASE_POINTS);
    }

    #[test]
    fn loyalty_card_earns_base_plus_bonus() {
        // R4: removed the duplicate test that checked the same invariant
        // with hard-coded 15 — the constant expression is the definitive form.
        assert_eq!(calculate_points(true), BASE_POINTS + LOYALTY_BONUS);
    }
}