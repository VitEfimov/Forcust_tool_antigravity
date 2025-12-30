export const cheatsheets = {
    Java: [
        {
            topic: "Entry Point",
            code: `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello Java");
    }
}`
        },
        {
            topic: "Variables and Data Types",
            code: `int a = 10;
long b = 20L;
double c = 10.5;
float d = 3.14f;
char e = 'A';
boolean flag = true;`
        },
        {
            topic: "Type Casting",
            code: `int x = (int) 10.5; // explicit casting
double y = 10;      // implicit casting`
        },
        {
            topic: "Control Flow",
            code: `if (a > 5) {
    System.out.println("Greater");
} else {
    System.out.println("Smaller");
}

for (int i = 0; i < 5; i++) {
    System.out.println(i);
}

while (a > 0) {
    a--;
}

do {
    a++;
} while (a < 5);`
        },
        {
            topic: "Arrays",
            code: `int[] arr = {1, 2, 3};
int[] arr2 = new int[3];

System.out.println(arr[0]);`
        },
        {
            topic: "Methods",
            code: `static int add(int a, int b) {
    return a + b;
}`
        },
        {
            topic: "Classes and Objects",
            code: `class Car {
    String model;

    void drive() {
        System.out.println("Driving");
    }
}

Car car = new Car();
car.drive();`
        },
        {
            topic: "Constructors",
            code: `class User {
    String name;

    User(String name) {
        this.name = name;
    }
}`
        },
        {
            topic: "Inheritance",
            code: `class A {
    void show() {}
}

class B extends A {
    void show() {}
}`
        },
        {
            topic: "Polymorphism",
            code: "A obj = new B(); // runtime polymorphism"
        },
        {
            topic: "Encapsulation",
            code: `class Person {
    private int age;

    public int getAge() {
        return age;
    }
}`
        },
        {
            topic: "Abstraction",
            code: `abstract class Shape {
    abstract void draw();
}`
        },
        {
            topic: "Interfaces",
            code: `interface Flyable {
    void fly();
}

class Bird implements Flyable {
    public void fly() {}
}`
        },
        {
            topic: "Modifiers",
            code: `public class Test {}
final class Constants {}
static int counter;`
        },
        {
            topic: "Exception Handling",
            code: `try {
    int x = 10 / 0;
} catch (ArithmeticException e) {
    e.printStackTrace();
} finally {
    System.out.println("Done");
}`
        },
        {
            topic: "Custom Exception",
            code: "class MyException extends RuntimeException {}"
        },
        {
            topic: "Collections - List",
            code: `List<String> list = new ArrayList<>();
list.add("A");`
        },
        {
            topic: "Collections - Set",
            code: "Set<String> set = new HashSet<>();"
        },
        {
            topic: "Collections - Map",
            code: `Map<String, Integer> map = new HashMap<>();
map.put("a", 1);`
        },
        {
            topic: "Generics",
            code: `class Box<T> {
    T value;
}`
        },
        {
            topic: "Lambda Expressions",
            code: "(x, y) -> x + y"
        },
        {
            topic: "Functional Interface",
            code: `@FunctionalInterface
interface Calc {
    int add(int a, int b);
}`
        },
        {
            topic: "Stream API",
            code: `list.stream()
    .filter(x -> x.startsWith("A"))
    .map(String::toUpperCase)
    .forEach(System.out::println);`
        },
        {
            topic: "Optional",
            code: `Optional<String> opt = Optional.of("Java");
opt.ifPresent(System.out::println);`
        },
        {
            topic: "Threads",
            code: `class MyThread extends Thread {
    public void run() {}
}

Runnable r = () -> {};
new Thread(r).start();`
        },
        {
            topic: "Executor Service",
            code: `ExecutorService ex = Executors.newFixedThreadPool(2);
ex.submit(() -> {});
ex.shutdown();`
        },
        {
            topic: "Synchronization",
            code: "synchronized void syncMethod() {}"
        },
        {
            topic: "File I/O",
            code: `Files.readAllLines(Path.of("file.txt"));`
        },
        {
            topic: "Equals vs ==",
            code: `String a = "Java";
String b = new String("Java");

System.out.println(a.equals(b)); // true
System.out.println(a == b);       // false`
        },
        {
            topic: "Immutable Class",
            code: `final class Immutable {
    private final int x;

    Immutable(int x) {
        this.x = x;
    }

    public int getX() {
        return x;
    }
}`
        },
        {
            topic: "Common Interview Trap",
            code: `Integer a = 128;
Integer b = 128;
System.out.println(a == b); // false`
        }
    ],
    FastAPI: [
        {
            topic: "Install FastAPI",
            code: "pip install fastapi uvicorn"
        },
        {
            topic: "Basic App",
            code: `from fastapi import FastAPI
app = FastAPI()

@app.get('/')
def read_root():
    return {'message': 'Hello World'}`
        },
        {
            topic: "Run Server",
            code: "uvicorn main:app --reload"
        },
        {
            topic: "Path Parameters",
            code: `@app.get('/items/{item_id}')
def read_item(item_id: int):
    return {'item_id': item_id}`
        },
        {
            topic: "Query Parameters",
            code: `@app.get('/items/')
def read_items(skip: int = 0, limit: int = 10):
    return {'skip': skip, 'limit': limit}`
        },
        {
            topic: "Request Body",
            code: `from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

@app.post('/items/')
def create_item(item: Item):
    return item`
        },
        {
            topic: "Response Model",
            code: `@app.get('/items/{id}', response_model=Item)
def read_item(id: int):
    return {'name': 'item', 'price': 10.5}`
        },
        {
            topic: "Dependencies",
            code: `from fastapi import Depends

def common_parameters(q: str = None):
    return q

@app.get('/items/')
def read_items(q: str = Depends(common_parameters)):
    return {'q': q}`
        },
        {
            topic: "Middleware",
            code: `from starlette.middleware.base import BaseHTTPMiddleware
@app.middleware('http')
async def add_process_time_header(request, call_next):
    response = await call_next(request)
    response.headers['X-Process-Time'] = '0.1'
    return response`
        },
        {
            topic: "Background Tasks",
            code: `from fastapi import BackgroundTasks

@app.post('/send/')
def send_email(background_tasks: BackgroundTasks):
    background_tasks.add_task(some_function)
    return {'message':'Email scheduled'}`
        },
        {
            topic: "Path Operation with Tags",
            code: `@app.get('/users/', tags=['users'])
def read_users():
    return []`
        }
    ],
    JavaScript: [
        { topic: "Variables", code: "let x = 10;\nconst y = 20;\nvar z = 30;" },
        { topic: "Data Types", code: "let num = 10;\nlet str = 'JS';\nlet bool = true;\nlet arr = [1,2,3];\nlet obj = {a:1, b:2};\nlet func = () => {};\nlet n = null;\nlet u = undefined;" },
        { topic: "Type Conversion", code: "let x = '10';\nlet y = Number(x);\nlet z = String(123);\nlet b = Boolean(0);" },
        { topic: "Operators", code: "let sum = 10 + 20;\nlet diff = 20 - 10;\nlet prod = 2 * 3;\nlet div = 10 / 2;\nlet mod = 10 % 3;\nlet exp = 2 ** 3;" },
        { topic: "Control Flow", code: "if(x>5){console.log('>5');} else {console.log('<=5');}\n\nfor(let i=0;i<5;i++){console.log(i);}\n\nwhile(x>0){x--;}\ndo{ x++; } while(x<5);" },
        { topic: "Functions", code: "function add(a,b){ return a+b; }\nconst multiply = (a,b) => a*b;" },
        { topic: "Arrow Functions", code: "const square = x => x*x;\nconst sum = (a,b) => a+b;" },
        { topic: "Objects", code: "let obj = {name:'JS', age:25};\nconsole.log(obj.name);\nobj.height = 180;" },
        { topic: "Destructuring", code: "const {name, age} = obj;\nconst [a,b] = [1,2];" },
        { topic: "Spread and Rest", code: "let arr1=[1,2]; let arr2=[...arr1,3,4];\nfunction sum(...nums){ return nums.reduce((a,b)=>a+b,0); }" },
        { topic: "Classes", code: "class Person {\n  constructor(name, age){ this.name=name; this.age=age; }\n  greet(){ console.log(`Hello, ${this.name}`); }\n}\nconst p = new Person('Alice',25); p.greet();" },
        { topic: "Inheritance", code: "class Animal { speak(){ console.log('Animal sound'); } }\nclass Dog extends Animal { speak(){ console.log('Bark'); } }\nnew Dog().speak();" },
        { topic: "Static Methods", code: "class MathUtil {\n  static add(a,b){ return a+b; }\n}\nconsole.log(MathUtil.add(2,3));" },
        { topic: "Getters and Setters", code: "class Circle {\n  constructor(radius){ this._radius = radius; }\n  get radius(){ return this._radius; }\n  set radius(r){ this._radius = r; }\n}\nlet c = new Circle(5); c.radius = 10;" },
        { topic: "Template Literals", code: "let name='JS'; console.log(`Hello ${name}`);" },
        { topic: "Promises", code: "let p = new Promise((resolve,reject)=>{ resolve('Done'); });\np.then(val => console.log(val));" },
        { topic: "Async/Await", code: "async function main(){ let res = await Promise.resolve('Hello'); console.log(res); }\nmain();" },
        { topic: "Error Handling", code: "try{ throw new Error('Oops'); } catch(e){ console.log(e.message); } finally{ console.log('Done'); }" },
        { topic: "Map", code: "let m = new Map(); m.set('a',1); console.log(m.get('a'));" },
        { topic: "Set", code: "let s = new Set([1,2,2,3]); console.log(s);" },
        { topic: "Array Methods", code: "[1,2,3].forEach(x=>console.log(x));\n[1,2,3].map(x=>x*2);\n[1,2,3].filter(x=>x>1);\n[1,2,3].reduce((a,b)=>a+b,0);" },
        { topic: "Destructuring Function Params", code: "function greet({name,age}){ console.log(`Hello ${name}, ${age}`); }\ngreet({name:'Alice',age:25});" },
        { topic: "Modules - ES6", code: "export const pi=3.14;\nimport {pi} from './module.js';" },
        { topic: "Modules - CommonJS", code: "module.exports = {pi:3.14};\nconst m = require('./module'); console.log(m.pi);" },
        { topic: "Optional Chaining", code: "let obj = {a:{b:2}};\nconsole.log(obj?.a?.b);\nconsole.log(obj?.x?.y);" },
        { topic: "Nullish Coalescing", code: "let x = null ?? 'default'; console.log(x);" },
        { topic: "Type Checking", code: "console.log(typeof 10);\nconsole.log(Array.isArray([1,2,3]));" },
        { topic: "Event Loop", code: "console.log('Start');\nsetTimeout(()=>console.log('Timeout'),0);\nconsole.log('End');" },
        { topic: "DOM Manipulation", code: "const el = document.getElementById('app'); el.textContent = 'Hello';" },
        { topic: "Fetch API", code: "fetch('https://api.example.com').then(res => res.json()).then(data=>console.log(data));" },
        { topic: "Destructuring Arrays", code: "const arr = [1,2,3]; const [a,b,...rest] = arr;" },
        { topic: "Rest and Spread in Objects", code: "const obj1 = {a:1,b:2}; const obj2 = {...obj1,c:3};" },
        { topic: "SetTimeout and SetInterval", code: "setTimeout(()=>console.log('Delayed'),1000);\nlet id = setInterval(()=>console.log('Repeat'),1000);\nclearInterval(id);" },
        { topic: "JSON Methods", code: "let obj = {a:1}; let str = JSON.stringify(obj);\nlet newObj = JSON.parse(str);" },
        { topic: "Closures", code: "function outer(x){ return function(y){ return x+y; }; }\nlet add5 = outer(5); console.log(add5(3));" },
        { topic: "Currying", code: "const add = a => b => a+b;\nconsole.log(add(2)(3));" },
        { topic: "Prototype", code: "function Person(name){ this.name=name; }\nPerson.prototype.greet = function(){ console.log(this.name); };\nlet p = new Person('Alice'); p.greet();" },
        { topic: "Classes & Prototype", code: "class Animal{ speak(){ console.log('Hi'); } } let a = new Animal(); a.speak();" },
        { topic: "Symbol", code: "const sym = Symbol('id'); console.log(sym);" },
        { topic: "Iterators & Generators", code: "function* gen(){ yield 1; yield 2; }\nlet g = gen(); console.log(g.next().value);" },
        { topic: "Promises All / Race", code: "Promise.all([p1,p2]).then(res=>console.log(res));\nPromise.race([p1,p2]).then(res=>console.log(res));" },
        { topic: "Error Throwing", code: "function test(){ throw new Error('Fail'); }\ntry{ test(); } catch(e){ console.log(e.message); }" },
        { topic: "Async Iterators", code: "async function* asyncGen(){ yield 1; yield 2; }\nfor await (let val of asyncGen()){ console.log(val); }" },
        { topic: "Modules Dynamic Import", code: "import('./module.js').then(m=>m.func());" }
    ],
    SQL: [
        { topic: "Select Statement", code: "SELECT * FROM employees;\nSELECT name, salary FROM employees WHERE salary > 50000;" },
        { topic: "Distinct", code: "SELECT DISTINCT department FROM employees;" },
        { topic: "Where Clause", code: "SELECT * FROM employees WHERE age >= 30 AND department = 'Sales';" },
        { topic: "Order By", code: "SELECT * FROM employees ORDER BY salary DESC, name ASC;" },
        { topic: "Group By", code: "SELECT department, COUNT(*) FROM employees GROUP BY department;" },
        { topic: "Having Clause", code: "SELECT department, AVG(salary) FROM employees GROUP BY department HAVING AVG(salary) > 50000;" },
        { topic: "Joins - Inner Join", code: "SELECT e.name, d.name FROM employees e INNER JOIN departments d ON e.dept_id = d.id;" },
        { topic: "Left Join", code: "SELECT e.name, d.name FROM employees e LEFT JOIN departments d ON e.dept_id = d.id;" },
        { topic: "Right Join", code: "SELECT e.name, d.name FROM employees e RIGHT JOIN departments d ON e.dept_id = d.id;" },
        { topic: "Full Outer Join", code: "SELECT e.name, d.name FROM employees e FULL OUTER JOIN departments d ON e.dept_id = d.id;" },
        { topic: "Subqueries", code: "SELECT name FROM employees WHERE salary > (SELECT AVG(salary) FROM employees);" },
        { topic: "Insert Statement", code: "INSERT INTO employees(name, age, department) VALUES ('Alice', 30, 'IT');" },
        { topic: "Update Statement", code: "UPDATE employees SET salary = salary * 1.1 WHERE department = 'Sales';" },
        { topic: "Delete Statement", code: "DELETE FROM employees WHERE age < 25;" },
        { topic: "Create Table", code: "CREATE TABLE employees (\n  id INT PRIMARY KEY,\n  name VARCHAR(50),\n  age INT,\n  salary DECIMAL(10,2),\n  department VARCHAR(50)\n);" },
        { topic: "Alter Table", code: "ALTER TABLE employees ADD COLUMN hire_date DATE;" },
        { topic: "Drop Table", code: "DROP TABLE employees;" },
        { topic: "Indexes", code: "CREATE INDEX idx_name ON employees(name);" },
        { topic: "Views", code: "CREATE VIEW high_salary AS SELECT name, salary FROM employees WHERE salary > 50000;" },
        { topic: "Transactions", code: "BEGIN;\nUPDATE employees SET salary = salary * 1.1;\nCOMMIT;" }
    ],
    'Spring Boot': [
        { topic: "Create Spring Boot App", code: "Use https://start.spring.io/ or Spring CLI: spring init --dependencies=web myapp" },
        { topic: "Main Application", code: "import org.springframework.boot.SpringApplication;\nimport org.springframework.boot.autoconfigure.SpringBootApplication;\n\n@SpringBootApplication\npublic class MyApp {\n    public static void main(String[] args) {\n        SpringApplication.run(MyApp.class, args);\n    }\n}" },
        { topic: "Rest Controller", code: "import org.springframework.web.bind.annotation.*;\n\n@RestController\n@RequestMapping('/api')\npublic class MyController {\n    @GetMapping('/hello')\n    public String hello(){ return 'Hello Spring Boot'; }\n}" },
        { topic: "Path Variables", code: "@GetMapping('/items/{id}')\npublic String getItem(@PathVariable int id){ return 'Item '+id; }" },
        { topic: "Request Params", code: "@GetMapping('/items')\npublic String getItem(@RequestParam int id){ return 'Item '+id; }" },
        { topic: "Post Request", code: "@PostMapping('/items')\npublic Item createItem(@RequestBody Item item){ return item; }" },
        { topic: "Service Layer", code: "@Service\npublic class ItemService {\n    public List<Item> getItems(){ return new ArrayList<>(); }\n}" },
        { topic: "Repository Layer", code: "@Repository\npublic interface ItemRepository extends JpaRepository<Item, Long> {}" },
        { topic: "Dependency Injection", code: "@Autowired\nprivate ItemService itemService;" },
        { topic: "Exception Handling", code: "@ControllerAdvice\npublic class GlobalExceptionHandler {\n    @ExceptionHandler(Exception.class)\n    public ResponseEntity<String> handleAll(){ return ResponseEntity.status(500).body('Error'); }\n}" },
        { topic: "Properties File", code: "spring.datasource.url=jdbc:mysql://localhost:3306/db\nspring.datasource.username=root\nspring.datasource.password=root" },
        { topic: "Profiles", code: "application-dev.properties\napplication-prod.properties\n@Profile('dev')\n@Service\npublic class DevService {}" },
        { topic: "Actuator", code: "Add dependency: spring-boot-starter-actuator\nAccess: /actuator/health /actuator/metrics" },
        { topic: "Logging", code: "import org.slf4j.Logger;\nimport org.slf4j.LoggerFactory;\nprivate static final Logger log = LoggerFactory.getLogger(MyController.class);\nlog.info('Message');" }
    ],
    Python: [
        {
            topic: "Print Statement",
            code: `print("Hello, Python")`
        },
        {
            topic: "Variables and Data Types",
            code: `x = 10
y = 3.14
name = 'Python'
flag = True
lst = [1,2,3]
tuple_data = (1,2,3)
dict_data = {'a':1, 'b':2}
set_data = {1,2,3}`
        },
        {
            topic: "Type Casting",
            code: `x = int(3.5)
y = float(10)`
        },
        {
            topic: "Control Flow",
            code: `if x > 5:
    print('Greater')
else:
    print('Smaller')

for i in range(5):
    print(i)

while x > 0:
    x -= 1`
        },
        {
            topic: "Functions",
            code: `def add(a, b):
    return a + b

result = add(2,3)`
        },
        {
            topic: "Lambda Expressions",
            code: `square = lambda x: x*x
print(square(5))`
        },
        {
            topic: "List Comprehensions",
            code: `squares = [x*x for x in range(5)]`
        },
        {
            topic: "String Operations",
            code: `s = 'Python'
print(s.upper())
print(s.lower())
print(s.replace('P','J'))`
        },
        {
            topic: "File I/O",
            code: `with open('file.txt','r') as f:
    content = f.read()

with open('file.txt','w') as f:
    f.write('Hello')`
        },
        {
            topic: "Exception Handling",
            code: `try:
    x = 1/0
except ZeroDivisionError:
    print('Error')
finally:
    print('Done')`
        },
        {
            topic: "Classes and Objects",
            code: `class Car:
    def __init__(self, model):
        self.model = model
    def drive(self):
        print('Driving')

car = Car('BMW')
car.drive()`
        },
        {
            topic: "Inheritance",
            code: `class A:
    def show(self):
        print('A')

class B(A):
    def show(self):
        print('B')

obj = B()
obj.show()`
        },
        {
            topic: "Decorators",
            code: `def decorator(func):
    def wrapper():
        print('Before')
        func()
        print('After')
    return wrapper

@decorator
def say_hello():
    print('Hello')

say_hello()`
        },
        {
            topic: "Modules and Imports",
            code: `import math
print(math.sqrt(16))
from math import pow
print(pow(2,3))`
        },
        {
            topic: "Sets",
            code: `s = {1,2,3}
s.add(4)
s.remove(2)`
        },
        {
            topic: "Dictionaries",
            code: `d = {'a':1,'b':2}
d['c'] = 3
print(d.get('b'))
for key, value in d.items():
    print(key, value)`
        },
        {
            topic: "List Methods",
            code: `lst = [1,2,3]
lst.append(4)
lst.pop()
lst.sort()`
        },
        {
            topic: "Tuples",
            code: `t = (1,2,3)
print(t[0])
# immutable`
        },
        {
            topic: "Generators",
            code: `def gen():
    for i in range(3):
        yield i

for x in gen():
    print(x)`
        },
        {
            topic: "Comprehensions - Dict",
            code: `d = {x:x*x for x in range(5)}`
        },
        {
            topic: "Comprehensions - Set",
            code: `s = {x*x for x in range(5)}`
        },
        {
            topic: "Decorators with Arguments",
            code: `def repeat(n):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(n): func(*args, **kwargs)
        return wrapper
    return decorator

@repeat(3)
def greet():
    print('Hi')

greet()`
        },
        {
            topic: "Context Managers",
            code: `with open('file.txt') as f:
    data = f.read()`
        },
        {
            topic: "Async/Await",
            code: `import asyncio

async def main():
    print('Hello')
    await asyncio.sleep(1)
    print('World')

asyncio.run(main())`
        },
        {
            topic: "Type Hints",
            code: `def add(a: int, b: int) -> int:
    return a + b`
        },
        {
            topic: "String Formatting",
            code: `name = 'Python'
print(f'Hello {name}')
print('Hello {}'.format(name))`
        },
        {
            topic: "Boolean Logic",
            code: `a = True
b = False
print(a and b)
print(a or b)
print(not a)`
        },
        {
            topic: "Common Built-in Functions",
            code: `print(len([1,2,3]))
print(sum([1,2,3]))
print(min([1,2,3]))
print(max([1,2,3]))`
        },
        {
            topic: "Enumerate",
            code: `lst = ['a','b']
for idx, val in enumerate(lst):
    print(idx, val)`
        },
        {
            topic: "Zip",
            code: `a = [1,2]
b = ['x','y']
for i,j in zip(a,b):
    print(i,j)`
        },
        {
            topic: "Sorting",
            code: `lst = [3,1,2]
lst.sort()
lst.sort(reverse=True)
sorted_lst = sorted(lst, key=lambda x: -x)`
        },
        {
            topic: "Comprehensions - Conditional",
            code: `even_squares = [x*x for x in range(10) if x%2==0]`
        },
        {
            topic: "Map/Filter/Reduce",
            code: `from functools import reduce
lst = [1,2,3]
print(list(map(lambda x: x*2, lst)))
print(list(filter(lambda x: x%2==0, lst)))
print(reduce(lambda a,b:a+b,lst))`
        },
        {
            topic: "Copy - Shallow/Deep",
            code: `import copy
lst = [[1]]
shallow = copy.copy(lst)
deep = copy.deepcopy(lst)`
        },
        {
            topic: "Pythonic Iteration",
            code: `for x in range(5):
    print(x)

for i, v in enumerate(['a','b']):
    print(i,v)`
        },
        {
            topic: "Class Definition",
            code: `class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    def greet(self):
        print(f'Hello, {self.name}')`
        },
        {
            topic: "Creating Object",
            code: `p = Person('Alice', 25)
p.greet()`
        },
        {
            topic: "Instance vs Class Variables",
            code: `class Dog:
    species = 'Canis'
    def __init__(self, name):
        self.name = name

d1 = Dog('Rex')
d2 = Dog('Fido')
print(d1.species, d2.species)`
        },
        {
            topic: "Inheritance",
            code: `class Animal:
    def speak(self):
        print('Animal sound')

class Dog(Animal):
    def speak(self):
        print('Bark')

d = Dog()
d.speak()`
        },
        {
            topic: "Multiple Inheritance",
            code: `class A:
    def show(self): print('A')
class B:
    def show(self): print('B')
class C(A,B): pass
c = C()
c.show()`
        },
        {
            topic: "super()",
            code: `class A:
    def __init__(self): print('A')
class B(A):
    def __init__(self):
        super().__init__()
        print('B')
B()`
        },
        {
            topic: "Method Overriding",
            code: `class Parent:
    def greet(self): print('Hello Parent')
class Child(Parent):
    def greet(self): print('Hello Child')
Child().greet()`
        },
        {
            topic: "Private and Protected",
            code: `class MyClass:
    _protected = 'Protected'
    __private = 'Private'

obj = MyClass()
print(obj._protected)
# print(obj.__private) # AttributeError`
        },
        {
            topic: "Class Methods",
            code: `class Person:
    count = 0
    @classmethod
    def increase_count(cls):
        cls.count += 1
Person.increase_count()
print(Person.count)`
        },
        {
            topic: "Static Methods",
            code: `class Math:
    @staticmethod
    def add(a,b):
        return a+b
print(Math.add(2,3))`
        },
        {
            topic: "Properties",
            code: `class Circle:
    def __init__(self, radius):
        self._radius = radius
    @property
    def radius(self):
        return self._radius
    @radius.setter
    def radius(self, r):
        self._radius = r
c = Circle(5)
c.radius = 10
print(c.radius)`
        },
        {
            topic: "Magic / Dunder Methods",
            code: `class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)
    def __repr__(self):
        return f'Vector({self.x}, {self.y})'
v1 = Vector(1,2)
v2 = Vector(3,4)
print(v1 + v2)`
        },
        {
            topic: "Operator Overloading",
            code: `class Number:
    def __init__(self, value): self.value = value
    def __mul__(self, other): return Number(self.value * other.value)
    def __repr__(self): return str(self.value)
print(Number(2) * Number(3))`
        },
        {
            topic: "Decorators (Function)",
            code: `def decorator(func):
    def wrapper(*args, **kwargs):
        print('Before')
        func(*args, **kwargs)
        print('After')
    return wrapper

@decorator
def hello():
    print('Hello')
hello()`
        },
        {
            topic: "Decorators (Class)",
            code: `def class_decorator(cls):
    cls.extra = 'Added'
    return cls

@class_decorator
class MyClass: pass
print(MyClass.extra)`
        },
        {
            topic: "Abstract Base Classes",
            code: `from abc import ABC, abstractmethod
class Shape(ABC):
    @abstractmethod
    def area(self): pass

class Square(Shape):
    def __init__(self, s): self.s = s
    def area(self): return self.s*self.s
print(Square(5).area())`
        },
        {
            topic: "Metaclasses",
            code: `class Meta(type):
    def __new__(cls, name, bases, dct):
        dct['added'] = lambda self: 'Hello'
        return super().__new__(cls, name, bases, dct)

class MyClass(metaclass=Meta): pass
print(MyClass().added())`
        },
        {
            topic: "Slots",
            code: `class MyClass:
    __slots__ = ['x','y']
    def __init__(self, x, y):
        self.x = x
        self.y = y
obj = MyClass(1,2)`
        },
        {
            topic: "Singleton Pattern",
            code: `class Singleton:
    _instance = None
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
s1 = Singleton()
s2 = Singleton()
print(s1 is s2)`
        },
        {
            topic: "Dynamic Attributes",
            code: `class A: pass
a = A()
a.x = 5
print(a.x)`
        },
        {
            topic: "Introspection",
            code: `class A:
    def method(self): pass
print(dir(A))
print(hasattr(A,'method'))`
        },
        {
            topic: "Context Managers in Classes",
            code: `class MyCM:
    def __enter__(self): print('Enter'); return self
    def __exit__(self, exc_type, exc_val, exc_tb): print('Exit')
with MyCM() as cm: pass`
        },
        {
            topic: "MRO (Method Resolution Order)",
            code: `class A: pass
class B(A): pass
class C(A): pass
class D(B,C): pass
print(D.__mro__)`
        },
        {
            topic: "Callable Objects",
            code: `class Adder:
    def __call__(self, a,b): return a+b
add = Adder()
print(add(2,3))`
        },
        {
            topic: "Property with Validation",
            code: `class Person:
    def __init__(self, age): self._age = age
    @property
    def age(self): return self._age
    @age.setter
    def age(self, value):
        if value<0: raise ValueError('Invalid')
        self._age = value
p = Person(10)
p.age = 20`
        }
    ]
};
