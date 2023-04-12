from interpret import Stack

if __name__ == "__main__":
    s = Stack()

    s.append("hello")
    s.append("world")
    print(s._first_elem)
    print(f"top: {s.get_top()}")
    s.pop()
    print(f"top: {s.get_top()}")
    s.pop()
    s.pop()
    s.pop()
    s.pop()
    print(f"top: {s.get_top()}")
