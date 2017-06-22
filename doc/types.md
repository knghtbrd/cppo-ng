# Special types used by cppo

- *hex-ustr*
  This is a standard Python3 string (UTF-8) containing two hex digits per byte.
  whose length should always be an even number.  No prefix or suffix is used,
  just the digits.  It's just a convenient way to specify an arbitrary stream
  of bytes in a human-readable format.  This is somewhat inefficient as
  implemented because the functions are designed to work in Python2 and
  Python3.

- *bin-ustr*
  Like hex-ustr but composed of only the digits 0 and 1.  You need eight of
  these to make a byte.  As with hex-ustr, functions operating on bin-ustr jump
  through hoops to be compatible with both Python2 and Python3.
