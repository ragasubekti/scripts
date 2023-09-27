import hashlib
import sqlite3
import os


def check_hash(file_path):
    with open(file_path, "rb") as f:
        md5 = hashlib.md5()
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()


def store_hash_in_db(db_path, file_path, hash):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, hash) VALUES (?, ?)",
              (file_path, hash))
    conn.commit()
    conn.close()


def check_hash_in_db(db_path, hash):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT file_path FROM files WHERE hash = ?", (hash,))
    file_path = c.fetchone()
    conn.close()
    return file_path


def delete_file(file_path):
    print("Delete" + file_path)
    # os.remove(file_path)


def main():
    db_path = "hashes.db"
    dir_path = "/"

    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE files (file_path TEXT, hash TEXT)")
        conn.commit()
        conn.close()

    for file_path in os.listdir(dir_path):
        print("Checking: " + file_path)
        hash = check_hash(os.path.join(dir_path, file_path))

        path_in_db = check_hash_in_db(db_path, hash)

        if path_in_db is not None:
            print([path_in_db[0], file_path, path_in_db[0] == file_path])

            if path_in_db[0] != file_path:
                # original_file_path = check_hash_in_db(db_path, hash)
                delete_file(os.path.join(dir_path, file_path))

        else:
            store_hash_in_db(db_path, file_path, hash)


if __name__ == "__main__":
    main()
