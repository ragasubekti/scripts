from ast import mod
import hashlib
import sqlite3
import os
import tqdm


def check_hash(file_path):
    with open(file_path, "rb") as f:
        md5 = hashlib.md5()
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()


def store_hash_in_db(db_path, file_path, hash, mtime):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, hash, modified_time) VALUES (?, ?, ?)",
              (file_path, hash, mtime))
    conn.commit()
    conn.close()


def check_file_mtime(db_path, file_path, mtime):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT hash FROM files WHERE file_path = ? AND modified_time = ?",
              (file_path, mtime))
    hash = c.fetchone()
    conn.close()
    return hash


def check_hash_in_db(db_path, hash):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT file_path FROM files WHERE hash = ?", (hash,))
    file_path = c.fetchone()
    conn.close()
    return file_path


def create_hard_link(file_path, new_file_path):
    if os.path.exists(new_file_path):
        print("\033[41m[REMOVING]\033[0m", end="")
        print(" {}".format(new_file_path))
        # os.remove(new_file_path)

    print("\033[42m[HARD_LINK]\033[0m", end="")
    print(" {} > {}".format(new_file_path, file_path))

    # os.link(file_path, new_file_path)


def delete_file(file_path):
    print("Delete" + file_path)
    # os.remove(file_path)


def get_total_items_in_folder(dir_path):
    total_items = 0
    for root, dirs, files in os.walk(dir_path):
        total_items += len(files) + len(dirs)
    return total_items


def main():
    db_path = "hashes.db"
    dir_path = "/archive/"

    total_items = get_total_items_in_folder(dir_path)
    progress_bar = tqdm.tqdm(total=total_items)

    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "CREATE TABLE files (file_path TEXT, hash TEXT, modified_time INTEGER)")
        conn.commit()
        conn.close()

    for root, dirs, files in os.walk(dir_path):
        for file_path in files:
            file_path = os.path.join(root, file_path)

            modified_time = os.path.getmtime(file_path)

            hash_file_mtime = check_file_mtime(
                db_path, file_path, modified_time)

            if hash_file_mtime:
                progress_bar.update()
                continue

            hash = check_hash(file_path)

            path_in_db = check_hash_in_db(db_path, hash)
            progress_bar.update()

            if path_in_db is not None:
                if path_in_db[0] != file_path:
                    create_hard_link(file_path, path_in_db[0])

            else:
                store_hash_in_db(db_path, file_path, hash, modified_time)

    progress_bar.close()


if __name__ == "__main__":
    main()
