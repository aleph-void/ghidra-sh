/* Relocation test (test/reloc-check.sh): data and code references of every kind gcc -fPIC emits
   for SH: absolute .long, PC-relative calls, GOT/PLT, GOTOFF. */
extern int ext_var;
extern int ext_func(int);
static int local_var = 5;
int table[4] = { 1, 2, 3, 4 };
int *ptr_to_table = &table[2];
int (*fp)(int) = ext_func;
int use(int i) { return ext_var + local_var + table[i & 3] + ext_func(i); }
