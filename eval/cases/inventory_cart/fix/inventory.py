"""Shopping cart."""


class Cart:
    def __init__(self):
        self.items = []

    def add(self, name, price, qty=1):
        if qty < 1:
            raise ValueError("qty must be >= 1")
        self.items.append((name, price, qty))

    def total(self, discount_pct=0):
        """Cart total after a percentage discount (0-100)."""
        if not 0 <= discount_pct <= 100:
            raise ValueError("discount_pct must be within 0..100")
        subtotal = sum(p * q for _, p, q in self.items)
        return round(subtotal * (1 - discount_pct / 100), 2)
