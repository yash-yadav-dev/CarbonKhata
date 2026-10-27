from pathlib import Path

objects = [
    b"BT",
    b"/F1 12 Tf",
    b"50 780 Td",
    b"(CARBONKHATA - SAMPLE ELECTRICITY BILL) Tj",
    b"0 -30 Td",
    b"(TEST DATA ONLY - NOT A REAL BILL) Tj",
    b"0 -40 Td",
    b"(Consumer ID: DEMO-001) Tj",
    b"0 -25 Td",
    b"(Billing Period: October 2026) Tj",
    b"0 -25 Td",
    b"(Electricity Consumed: 1250 kWh) Tj",
    b"0 -25 Td",
    b"(Total Amount: INR 18450) Tj",
    b"ET"
]
stream = b"\n".join(objects)

content = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
    b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
    b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    + b"5 0 obj << /Length " + str(len(stream)).encode()
    + b" >> stream\n" + stream + b"\nendstream endobj\n"
)

offsets = [0]
for marker in [b"1 0 obj", b"2 0 obj", b"3 0 obj", b"4 0 obj", b"5 0 obj"]:
    offsets.append(content.index(marker))

xref_offset = len(content)
xref = b"xref\n0 6\n0000000000 65535 f \n"
for offset in offsets[1:]:
    xref += f"{offset:010d} 00000 n \n".encode()

content += (
    b"xref\n0 6\n0000000000 65535 f \n"
    + b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    + b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n"
    + str(xref_offset).encode() + b"\n%%EOF\n"
)

Path("sample_electricity_bill.pdf").write_bytes(content)
print("Synthetic electricity bill created successfully.")
