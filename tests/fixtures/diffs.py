"""Sample diff fixtures for testing."""

# Simple single-line change
SIMPLE_MODIFICATION = """\
@@ -10,7 +10,7 @@ class Calculator:
     def __init__(self):
         self.value = 0

-    def add(self, x):
+    def add(self, x: int) -> int:
         return self.value + x

     def subtract(self, x):
"""

# Addition of new code
NEW_FUNCTION_ADDITION = """\
@@ -20,6 +20,15 @@ class Calculator:
     def subtract(self, x):
         return self.value - x

+    def multiply(self, x: int) -> int:
+        \"\"\"Multiply the value by x.
+
+        Args:
+            x: The multiplier.
+
+        Returns:
+            The result of multiplication.
+        \"\"\"
+        return self.value * x
+
     def reset(self):
         self.value = 0
"""

# Deletion of code
CODE_DELETION = """\
@@ -15,12 +15,6 @@ class Calculator:
     def add(self, x):
         return self.value + x

-    def subtract(self, x):
-        # This method is deprecated
-        # Use sub() instead
-        print("Warning: subtract() is deprecated")
-        return self.value - x
-
     def sub(self, x):
         return self.value - x
"""

# Multiple hunks in a single file
MULTIPLE_HUNKS = """\
@@ -5,7 +5,7 @@ import logging
 from typing import Any

-logger = logging.getLogger(__name__)
+logger = logging.getLogger("myapp")


 class Service:
@@ -25,7 +25,8 @@ class Service:

     def process(self, data: dict) -> dict:
-        result = self._validate(data)
+        if not data:
+            raise ValueError("Data cannot be empty")
+        result = self._validate(data)
         return self._transform(result)
"""

# Large diff with many changes
LARGE_DIFF = """\
@@ -1,50 +1,60 @@ def process_items(items):
-    \"\"\"Process items.\"\"\"
+    \"\"\"Process items with validation and logging.
+
+    Args:
+        items: List of items to process.
+
+    Returns:
+        Processed items list.
+
+    Raises:
+        ValueError: If items is empty.
+    \"\"\"
+    if not items:
+        raise ValueError("Items cannot be empty")
+
+    logger.info("Processing %d items", len(items))
     results = []
+
     for item in items:
-        if item is None:
-            continue
-        if item.get("type") == "A":
-            result = process_type_a(item)
-        elif item.get("type") == "B":
-            result = process_type_b(item)
-        else:
-            result = process_default(item)
-        results.append(result)
+        try:
+            if item is None:
+                logger.warning("Skipping None item")
+                continue
+
+            item_type = item.get("type", "default")
+            processor = PROCESSORS.get(item_type, process_default)
+            result = processor(item)
+
+            if result.is_valid():
+                results.append(result)
+            else:
+                logger.warning("Invalid result for item: %s", item)
+
+        except ProcessingError as e:
+            logger.error("Failed to process item: %s", e)
+            continue
+
+    logger.info("Successfully processed %d items", len(results))
     return results
"""

# Binary file indicator
BINARY_FILE_DIFF = "Binary files a/image.png and b/image.png differ"

# Empty patch (file renamed without content change)
RENAME_ONLY_DIFF = ""

# Security-sensitive code (for testing security review)
SECURITY_ISSUE_DIFF = """\
@@ -15,6 +15,12 @@ def get_user(user_id):
     return db.query(f"SELECT * FROM users WHERE id = {user_id}")


+def execute_command(cmd):
+    \"\"\"Execute a shell command.\"\"\"
+    import subprocess
+    return subprocess.call(cmd, shell=True)
+
+
 def authenticate(username, password):
     \"\"\"Authenticate a user.\"\"\"
     user = db.query(f"SELECT * FROM users WHERE username = '{username}'")
"""

# Performance issue code
PERFORMANCE_ISSUE_DIFF = """\
@@ -10,7 +10,12 @@ def find_duplicates(items):
     duplicates = []
     for i in range(len(items)):
         for j in range(len(items)):
-            if i != j and items[i] == items[j]:
-                duplicates.append(items[i])
+            if i != j:
+                if items[i] == items[j]:
+                    if items[i] not in duplicates:
+                        duplicates.append(items[i])
+                        # Also log for debugging
+                        for k in range(len(items)):
+                            print(f"Checking {items[k]}")
     return duplicates
"""
