class QueueNode:
    def __init__(self, pnr, passenger, train_no, journey_date):
        self.pnr, self.passenger = pnr, passenger
        self.train_no, self.journey_date = train_no, journey_date
        self.next = None


class WaitingQueue:
    """FIFO queue (linked implementation): enqueue at REAR, dequeue from FRONT."""
    def __init__(self):
        self.front = self.rear = None
        self.size = 0

    def enqueue(self, node):
        if self.rear is None:
            self.front = self.rear = node
        else:
            self.rear.next = node
            self.rear = node
        self.size += 1

    def dequeue(self):
        if self.front is None:
            return None
        node = self.front
        self.front = node.next
        if self.front is None:
            self.rear = None
        node.next = None
        self.size -= 1
        return node

    def peek(self):
        return self.front

    def is_empty(self):
        return self.front is None

    def remove(self, pnr):                        # used when a waiting ticket is cancelled
        prev, cur = None, self.front
        while cur:
            if cur.pnr == pnr:
                if prev: prev.next = cur.next
                else: self.front = cur.next
                if cur is self.rear: self.rear = prev
                cur.next = None
                self.size -= 1
                return cur
            prev, cur = cur, cur.next
        return None

    def position(self, pnr):
        for i, n in enumerate(self.to_nodes(), 1):
            if n.pnr == pnr:
                return i
        return None

    def to_nodes(self):
        out, cur = [], self.front
        while cur:
            out.append(cur)
            cur = cur.next
        return out

    def to_list(self):
        return [{"pnr": n.pnr, "passenger": n.passenger, "position": i}
                for i, n in enumerate(self.to_nodes(), 1)]

    def __len__(self):
        return self.size
