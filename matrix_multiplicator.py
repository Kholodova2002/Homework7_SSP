import multiprocessing
from multiprocessing import Pool, Lock, Queue, Process
import random
import time
import os

def read_matrix(filename):
    """
    Читает матрицу из файла.
    Каждая строка файла соответствует строке матрицы,
    а элементы разделены пробелами.
    """
    with open(filename, 'r') as file:
        matrix = []
        for line in file:
            if line.strip():  # Пропускаем пустые строки
                row = list(map(float, line.strip().split()))
                matrix.append(row)
    return matrix

def write_matrix(filename, matrix):
    """
    Записывает матрицу в файл.
    Каждая строка матрицы записывается как строка в файле,
    элементы разделены пробелами.
    """
    with open(filename, 'w') as file:
        for row in matrix:
            line = ' '.join(map(str, row))
            file.write(line + '\n')

def compute_element(args):
    """
    Вычисляет значение одного элемента результирующей матрицы.
    Возвращает кортеж (i, j, результат).
    """
    i, j, A, B = args
    N = len(A[0])
    result = 0
    for k in range(N):
        result += A[i][k] * B[k][j]
    return (i, j, result)

def multiply_matrices(A, B, num_processes=None):
    """
    Перемножает матрицы A и B с использованием пула процессов.
    Возвращает результирующую матрицу C.
    """
    if not A or not B:
        raise ValueError("Матрицы не могут быть пустыми")
    if len(A[0]) != len(B):
        raise ValueError("Число столбцов первой матрицы должно равняться числу строк второй матрицы")
    
    rows_A, cols_A = len(A), len(A[0])
    cols_B = len(B[0])
    
    # Подготовка аргументов для каждой задачи
    tasks = [(i, j, A, B) for i in range(rows_A) for j in range(cols_B)]
    
    # Автоматическое определение количества процессов, если не задано
    if num_processes is None:
        num_processes = multiprocessing.cpu_count()
    
    # Создание пула процессов
    with Pool(processes=num_processes) as pool:
        results = pool.map(compute_element, tasks)
    
    # Формирование результирующей матрицы
    C = [[0 for _ in range(cols_B)] for _ in range(rows_A)]
    for i, j, value in results:
        C[i][j] = value
    
    return C

def compute_and_write(args):
    """
    Вычисляет элемент и записывает его в промежуточный файл.
    Возвращает кортеж (i, j, результат).
    """
    i, j, A, B, lock, filename = args
    N = len(A[0])
    result = 0
    for k in range(N):
        result += A[i][k] * B[k][j]
    
    # Запись в файл с использованием блокировки
    with lock:
        with open(filename, 'a') as file:
            file.write(f"{i} {j} {result}\n")
    return (i, j, result)

def multiply_matrices_with_intermediate_write(A, B, intermediate_file, num_processes=None):
    """
    Перемножает матрицы A и B, записывая промежуточные результаты в файл.
    Возвращает результирующую матрицу C.
    """
    if not A or not B:
        raise ValueError("Матрицы не могут быть пустыми")
    if len(A[0]) != len(B):
        raise ValueError("Число столбцов первой матрицы должно равняться числу строк второй матрицы")
    
    rows_A, cols_A = len(A), len(A[0])
    cols_B = len(B[0])
    
    # Очистка или создание промежуточного файла
    with open(intermediate_file, 'w') as f:
        pass  # Просто открываем файл для очистки
    
    lock = Lock()
    tasks = [(i, j, A, B, lock, intermediate_file) for i in range(rows_A) for j in range(cols_B)]
    
    # Автоматическое определение количества процессов, если не задано
    if num_processes is None:
        num_processes = multiprocessing.cpu_count()
    
    with Pool(processes=num_processes) as pool:
        results = pool.map(compute_and_write, tasks)
    
    # Формирование результирующей матрицы из результатов
    C = [[0 for _ in range(cols_B)] for _ in range(rows_A)]
    for i, j, value in results:
        C[i][j] = value
    
    return C

def get_num_processes():
    """
    Возвращает количество доступных процессоров.
    """
    return multiprocessing.cpu_count()

def generate_random_matrix(size):
    """
    Генерирует случайную квадратную матрицу заданного размера.
    Элементы матрицы — случайные числа от 0 до 1.
    """
    return [[random.random() for _ in range(size)] for _ in range(size)]

def generate_random_matrix_process(size, queue, num_matrices, matrix_type='A'):
    """
    Процесс генерации случайных матриц.
    Помещает сгенерированные матрицы в очередь.
    После генерации всех матриц помещает None для сигнала завершения.
    """
    for _ in range(num_matrices):
        matrix = generate_random_matrix(size)
        queue.put(matrix)
        print(f"Генерируется матрица {matrix_type}")
        time.sleep(0.1)  # Имитация задержки генерации
    queue.put(None)  # Сигнал завершения
    print(f"Генерация матриц {matrix_type} завершена.")

def multiply_matrices_async(queue_A, queue_B, result_queue, size):
    """
    Асинхронно перемножает матрицы, полученные из очередей.
    Помещает результирующие матрицы в result_queue.
    Завершается при получении None из любой очереди.
    """
    while True:
        A = queue_A.get()
        B = queue_B.get()
        if A is None or B is None:
            break
        C = multiply_matrices(A, B)
        result_queue.put(C)
        print("Перемножена пара матриц.")
    result_queue.put(None)
    print("Асинхронное перемножение завершено.")

def async_multiplication_demo(size=100, num_matrices=5):
    """
    Демонстрация асинхронной генерации и перемножения матриц.
    """
    queue_A = Queue()
    queue_B = Queue()
    result_queue = Queue()
    
    generator_A = Process(target=generate_random_matrix_process, args=(size, queue_A, num_matrices, 'A'))
    generator_B = Process(target=generate_random_matrix_process, args=(size, queue_B, num_matrices, 'B'))
    multiplier = Process(target=multiply_matrices_async, args=(queue_A, queue_B, result_queue, size))
    
    generator_A.start()
    generator_B.start()
    multiplier.start()
    
    completed = 0
    while True:
        C = result_queue.get()
        if C is None:
            break
        # Здесь можно обработать результирующую матрицу C
        print(f"Получена результирующая матрица {completed + 1}")
        completed += 1
    
    generator_A.join()
    generator_B.join()
    multiplier.join()
    print(f"Все {completed} матриц успешно перемножены.")

def main():
    """
    Основная функция программы.
    Предлагает пользователю выбрать режим работы:
    1. Перемножение матриц из файлов.
    2. Перемножение матриц из файлов с записью промежуточных результатов.
    3. Генерация случайных матриц и их асинхронное перемножение.
    """
    print("Параллельное перемножение матриц с использованием multiprocessing")
    print("Выберите режим работы:")
    print("1. Перемножение матриц из файлов.")
    print("2. Перемножение матриц из файлов с записью промежуточных результатов.")
    print("3. Генерация случайных матриц и их асинхронное перемножение.")
    choice = input("Введите номер режима (1/2/3): ")
    
    if choice == '1':
        # Режим 1: Перемножение матриц из файлов
        matrix1_file = input("Введите имя файла первой матрицы (например, matrix1.txt): ")
        matrix2_file = input("Введите имя файла второй матрицы (например, matrix2.txt): ")
        result_file = input("Введите имя файла для записи результата (например, result_matrix.txt): ")
        
        if not os.path.exists(matrix1_file):
            print(f"Файл {matrix1_file} не найден.")
            return
        if not os.path.exists(matrix2_file):
            print(f"Файл {matrix2_file} не найден.")
            return
        
        A = read_matrix(matrix1_file)
        B = read_matrix(matrix2_file)
        
        print("Перемножение матриц...")
        C = multiply_matrices(A, B)
        
        write_matrix(result_file, C)
        print(f"Результат записан в файл {result_file}")
    
    elif choice == '2':
        # Режим 2: Перемножение матриц из файлов с записью промежуточных результатов
        matrix1_file = input("Введите имя файла первой матрицы (например, matrix1.txt): ")
        matrix2_file = input("Введите имя файла второй матрицы (например, matrix2.txt): ")
        intermediate_file = input("Введите имя промежуточного файла (например, intermediate_results.txt): ")
        result_file = input("Введите имя файла для записи результата (например, result_matrix.txt): ")
        
        if not os.path.exists(matrix1_file):
            print(f"Файл {matrix1_file} не найден.")
            return
        if not os.path.exists(matrix2_file):
            print(f"Файл {matrix2_file} не найден.")
            return
        
        A = read_matrix(matrix1_file)
        B = read_matrix(matrix2_file)
        
        print("Перемножение матриц с записью промежуточных результатов...")
        C = multiply_matrices_with_intermediate_write(A, B, intermediate_file)
        
        write_matrix(result_file, C)
        print(f"Результат записан в файл {result_file}")
        print(f"Промежуточные результаты записаны в файл {intermediate_file}")
    
    elif choice == '3':
        # Режим 3: Генерация случайных матриц и их асинхронное перемножение
        try:
            size = int(input("Введите размерность квадратных матриц (например, 100): "))
            num_matrices = int(input("Введите количество матриц для генерации и перемножения (например, 5): "))
        except ValueError:
            print("Некорректный ввод. Размерность и количество должны быть целыми числами.")
            return
        
        print("Запуск асинхронной генерации и перемножения матриц...")
        async_multiplication_demo(size, num_matrices)
    
    else:
        print("Некорректный выбор режима.")

if __name__ == "__main__":
    main()