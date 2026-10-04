Plan for textutil.slugify:
1. Simple words: "Hello World" -> "hello-world".
2. Punctuation runs collapse to one dash: "Hello, World!" -> "hello-world".
3. Leading/trailing junk stripped.
4. Already-slug input is unchanged.
