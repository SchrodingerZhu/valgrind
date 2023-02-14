#ifndef __CG_ADDR_TUPLE_H
#define __CG_ADDR_TUPLE_H

struct TupleNode {
    struct TupleNode * next;
    char * name;
    Addr base;
    ULong size;
};

typedef  struct TupleNode tuple_node_t;

extern tuple_node_t* tuples;

__attribute__((always_inline))
static __inline__ void parse_address_tuples(const char * input) {
    // input: "NAME,N,M;"
    int state = 0;
    int cursor = 0;

    tuple_node_t current;
    current.size = 0;
    current.base = 0;
    current.name = NULL;
    current.next = NULL;

    while (1) {
        if(input[cursor] == 0 || input[cursor] == ';') {
            state = 0;
            input = input + cursor + 1;
            cursor = 0;
            tuple_node_t * mem = VG_(malloc)("cg_sim.tuple_node", sizeof(tuple_node_t));
            *mem = current;
            current.size = 0;
            current.base = 0;
            current.name = NULL;
            current.next = NULL;
            mem->next = tuples;
            tuples = mem;
            VG_(printf)("address tuple: %s,%lu,%llu\n", mem->name, mem->base, mem->size);
            if(input[-1] == 0) {
                break;
            }
        }
        if(input[cursor] == ',') {
            if (state == 0) {
                current.name = VG_(malloc)("cg_sim.tuple_node.name", cursor + 1);
                VG_(memcpy)(current.name, input, cursor);
                current.name[cursor] = 0;
            }
            state += 1;
        } else if (state == 1) {
            current.base = current.base * 10 + (input[cursor] - '0');
        } else if (state == 2) {
            current.size = current.size * 10 + (input[cursor] - '0');
        }
        cursor++;
    }
}


__attribute__((always_inline))
static __inline__ void parse_address_tuples_from_environ(void) {
    const char * name = "ADDRESS_TUPLES";
    const char * input = VG_(getenv)(name);
    if (input) parse_address_tuples(input);
}

__attribute__((always_inline))
static __inline__ void cleanup_address_tuples(void) {
    tuple_node_t * y;
    for (tuple_node_t * x = tuples; x != NULL;) {
        y = x->next;
        if (x->name) VG_(free)(x->name);
        VG_(free)(x);
        x = y;
    }
}




#endif // __CG_ADDR_TUPLE_H