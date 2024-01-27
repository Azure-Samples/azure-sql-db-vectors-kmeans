import pyodbc
import struct

def array_to_vector(a:list[float])->bytearray:
    # header
    b = bytearray([169, 170])

    # number of items
    b += bytearray(struct.pack("i", len(a)))
    pf = f"{len(a)}f"

    # filler
    b += bytearray([0,0])

    # items
    b += bytearray(struct.pack(pf, *a))

    return b

def vector_to_array(b:bytearray)->list[float]:
    # header
    h = struct.unpack_from("2B", b, 0)    
    assert h == (169,170)

    c = int(struct.unpack_from("i", b, 2)[0])
    pf = f"{c}f"
    a = struct.unpack_from(pf, b, 8)
    return a

def main():
    uid = "benchmark"
    pwd = "B3nch_mark"
    connection_string = (
        r"DRIVER={ODBC Driver 18 for SQL Server};"
        r"SERVER=localhost;"
        r"DATABASE=vectordb;"
        f"UID={uid};PWD={pwd};TrustServerCertificate=Yes"
    )
    items:float = [100, 2000, 1, 0, -1, 0.3, 200]

    b = array_to_vector(items);

    cnxn = pyodbc.connect(connection_string, autocommit=True)
    crsr = cnxn.cursor()
    crsr.execute("insert into dbo.test_vector_binary ([vector]) values (?)", b)
    crsr.close()

    a = vector_to_array(b)
    print(a)

if __name__ == "__main__":
    main()