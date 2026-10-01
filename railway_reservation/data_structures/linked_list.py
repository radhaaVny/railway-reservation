class BookingNode:
    """One confirmed booking = one node."""
    def __init__(self, pnr, passenger, train_no, seat, journey_date, status="CONFIRMED"):
        self.pnr, self.passenger, self.train_no = pnr, passenger, train_no
        self.seat, self.journey_date, self.status = seat, journey_date, status
        self.next = None


class BookingLinkedList:
    """Singly linked list of confirmed bookings (head -> ... -> NULL)."""
    def __init__(self):
        self.head, self.size = None, 0

    def append(self, node):                       # insertion at tail
        if self.head is None:
            self.head = node
        else:
            cur = self.head
            while cur.next:
                cur = cur.next
            cur.next = node
        self.size += 1

    def remove(self, pnr):                        # deletion by PNR
        prev, cur = None, self.head
        while cur:
            if cur.pnr == pnr:
                if prev: prev.next = cur.next
                else: self.head = cur.next
                cur.next = None
                self.size -= 1
                return cur
            prev, cur = cur, cur.next
        return None

    def find(self, pnr):
        for n in self.traverse():
            if n.pnr == pnr:
                return n
        return None

    def traverse(self):                           # traversal
        cur = self.head
        while cur:
            yield cur
            cur = cur.next

    def seats(self):
        return {n.seat for n in self.traverse()}

    def to_list(self):
        return [{"pnr": n.pnr, "passenger": n.passenger, "seat": n.seat} for n in self.traverse()]

    def __len__(self):
        return self.size
