import mysql.connector
from colorama import Fore, Back, Style, init
init(autoreset=True)



class DBManager:
    def __init__(self, config, host, port, user, password, database, max_snapshots, reset_board=False, reset_snapshots=False): #, board_width, board_height, default_color):
        print("[DBManager] Initializing...")
        try:
            self._connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
        except mysql.connector.Error as err:
            print(f"[DBManager] {Fore.YELLOW}|::| Failed to connect to DB {user}@{host}!")
            print(f"[DBManager] {Fore.YELLOW}|::| Working in VOLATILE mode!")
            config.set_volatile_mode()
            self._connection = None
            return

        if self._connection.is_connected():
            print(f"[DBManager] Connected to DB {user}@{host}!")
        else:
            print(f"[DBManager] {Fore.YELLOW}|::| Failed to connect to DB {user}@{host}!")
            print(f"[DBManager] {Fore.YELLOW}|::| Working in VOLATILE mode!")
            config.set_volatile_mode()

        self.reset_db(reset_board, reset_snapshots)

        self._max_snapshots = max_snapshots

        print("[DBManager] Ready")

    def __del__(self):
        self._close_connection()

    def _close_connection(self):
        # Implement connection closure logic here
        if self._connection:
            self._connection.close()
            print(f"[DBManager] Closed connection to DB {self._connection}!")
            self._connection = None

    def modify_pixel(self, x: int, y: int, hex_color: int):
        if not self._connection:
            return

        cursor = self._connection.cursor()

        byte_color = bytes.fromhex(hex(hex_color)[2:].zfill(6)[:6])
        try:
            query = "INSERT INTO pixel_board (x, y, color) VALUES (%s, %s, %s)"
            cursor.execute(query, (x, y, byte_color))
            print(f"[DBManager] Created pixel at ({x}, {y}) to color {hex_color}")
        except Exception as e:
            query = "UPDATE pixel_board SET color = %s WHERE x = %s AND y = %s"
            cursor.execute(query, (byte_color, x, y))
            print(f"[DBManager] Modified pixel at ({x}, {y}) to color {hex_color}")
        finally:
            self.commit()
            cursor.close()

    def create_quick_snapshot(self, name: str):
        if not self._connection:
            return

        try:
            cursor = self._connection.cursor()
            query = "SELECT CreateQuickSnapshot(%s)"
            cursor.execute(query, (name,))
            snapshot_id = cursor.fetchone()[0]
            print(f"[DBManager] Created quick snapshot '{name}' (id in DB: {snapshot_id})")

            if snapshot_id > self._max_snapshots:
                query = "DELETE FROM snapshots ORDER BY id ASC LIMIT 1"
                cursor.execute(query)
        except Exception as e:
            print(f"[DBManager] Failed to create quick snapshot '{name}': {e}")
        finally:
            self.commit()
            cursor.close()

    def reset_db(self, reset_board=True, reset_snapshots=True):
        if not self._connection:
            return

        cursor = self._connection.cursor()
        query = "TRUNCATE TABLE pixel_board"
        if reset_board:
            cursor.execute(query)
        query = "DELETE FROM snapshots"
        if reset_snapshots:
            cursor.execute(query)
        query = "DELETE FROM snapshot_pixels"
        if reset_snapshots:
            cursor.execute(query)
        query = "ALTER TABLE snapshots AUTO_INCREMENT = 1"
        if reset_snapshots:
            cursor.execute(query)
        if reset_snapshots or reset_board:
            print("[DBManager] !!!RESET DATABASE!!! !!!THIS IS SO WRONG!!! !!!POLICE ASSAULT IN PROGRESS!!! !!!PLEASE INVESTIGATE!!!")
            self.commit()
        cursor.close()

    def get_pixels(self):
        if not self._connection:
            return

        try:
            cursor = self._connection.cursor()
            query = "SELECT x, y, color FROM pixel_board"
            cursor.execute(query)
            pixels = cursor.fetchall()
            print(f"[DBManager] Retrieved {len(pixels)} pixels")
            return pixels
        except Exception as e:
            print(f"[DBManager] Failed to retrieve pixels: {e}")
        finally:
            cursor.close()

    def commit(self):
        if not self._connection:
            return

        print("[DBManager] Commit")
        self._connection.commit()
