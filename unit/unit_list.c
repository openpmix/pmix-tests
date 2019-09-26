/* -*- Mode: C; c-basic-offset:4 ; -*- */
/*
 * Copyright (c) 2004-2005 The Trustees of Indiana University and Indiana
 *                         University Research and Technology
 *                         Corporation.  All rights reserved.
 * Copyright (c) 2004-2006 The University of Tennessee and The University
 *                         of Tennessee Research Foundation.  All rights
 *                         reserved.
 * Copyright (c) 2004-2007 High Performance Computing Center Stuttgart,
 *                         University of Stuttgart.  All rights reserved.
 * Copyright (c) 2004-2005 The Regents of the University of California.
 *                         All rights reserved.
 * Copyright (c) 2007      Voltaire All rights reserved.
 * Copyright (c) 2013-2019 Intel, Inc.  All rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */

#include "pmix_common.h"
#include "unit_list.h"

/*
 *  List classes
 */

static void unit_list_item_construct(unit_list_item_t*);
static void unit_list_item_destruct(unit_list_item_t*);

PMIX_CLASS_INSTANCE(
    unit_list_item_t,
    pmix_object_t,
    unit_list_item_construct,
    unit_list_item_destruct
);

static void unit_list_construct(unit_list_t*);
static void unit_list_destruct(unit_list_t*);

PMIX_CLASS_INSTANCE(
    unit_list_t,
    pmix_object_t,
    unit_list_construct,
    unit_list_destruct
);


/*
 *
 *      unit_list_link_item_t interface
 *
 */

static void unit_list_item_construct(unit_list_item_t *item)
{
    item->unit_list_next = item->unit_list_prev = NULL;
    item->item_free = 1;
    item->unit_list_item_refcount = 0;
    item->unit_list_item_belong_to = NULL;
}

static void unit_list_item_destruct(unit_list_item_t *item)
{
    assert( 0 == item->unit_list_item_refcount );
    assert( NULL == item->unit_list_item_belong_to );
}


/*
 *
 *      unit_list_list_t interface
 *
 */

static void unit_list_construct(unit_list_t *list)
{
    /* These refcounts should never be used in assertions because they
       should never be removed from this list, added to another list,
       etc.  So set them to sentinel values. */

    PMIX_CONSTRUCT( &(list->unit_list_sentinel), unit_list_item_t );
    list->unit_list_sentinel.unit_list_item_refcount  = 1;
    list->unit_list_sentinel.unit_list_item_belong_to = list;

    list->unit_list_sentinel.unit_list_next = &list->unit_list_sentinel;
    list->unit_list_sentinel.unit_list_prev = &list->unit_list_sentinel;
    list->unit_list_length = 0;
}


/*
 * Reset all the pointers to be NULL -- do not actually destroy
 * anything.
 */
static void unit_list_destruct(unit_list_t *list)
{
    unit_list_construct(list);
}


/*
 * Insert an item at a specific place in a list
 */
bool unit_list_insert(unit_list_t *list, unit_list_item_t *item, long long idx)
{
    /* Adds item to list at index and retains item. */
    int     i;
    volatile unit_list_item_t *ptr, *next;

    if ( idx >= (long long)list->unit_list_length ) {
        return false;
    }

    if ( 0 == idx )
    {
        unit_list_prepend(list, item);
    } else {
        /* Spot check: ensure that this item is previously on no
           lists */

        assert(0 == item->unit_list_item_refcount);
        /* pointer to element 0 */
        ptr = list->unit_list_sentinel.unit_list_next;
        for ( i = 0; i < idx-1; i++ )
            ptr = ptr->unit_list_next;

        next = ptr->unit_list_next;
        item->unit_list_next = next;
        item->unit_list_prev = ptr;
        next->unit_list_prev = item;
        ptr->unit_list_next = item;

        /* Spot check: ensure this item is only on the list that we
           just insertted it into */

        item->unit_list_item_refcount += 1;
        assert(1 == item->unit_list_item_refcount);
        item->unit_list_item_belong_to = list;
    }

    list->unit_list_length++;
    return true;
}


static
void
unit_list_transfer(unit_list_item_t *pos, unit_list_item_t *begin,
                   unit_list_item_t *end)
{
    volatile unit_list_item_t *tmp;

    if (pos != end) {
        /* remove [begin, end) */
        end->unit_list_prev->unit_list_next = pos;
        begin->unit_list_prev->unit_list_next = end;
        pos->unit_list_prev->unit_list_next = begin;

        /* splice into new position before pos */
        tmp = pos->unit_list_prev;
        pos->unit_list_prev = end->unit_list_prev;
        end->unit_list_prev = begin->unit_list_prev;
        begin->unit_list_prev = tmp;
        {
            volatile unit_list_item_t* item = begin;
            while( pos != item ) {
                item->unit_list_item_belong_to = pos->unit_list_item_belong_to;
                item = item->unit_list_next;
                assert(NULL != item);
            }
        }
    }
}


void
unit_list_join(unit_list_t *thislist, unit_list_item_t *pos,
               unit_list_t *xlist)
{
    if (0 != unit_list_get_size(xlist)) {
        unit_list_transfer(pos, unit_list_get_first(xlist),
                           unit_list_get_end(xlist));

        /* fix the sizes */
        thislist->unit_list_length += xlist->unit_list_length;
        xlist->unit_list_length = 0;
    }
}


void
unit_list_splice(unit_list_t *thislist, unit_list_item_t *pos,
                 unit_list_t *xlist, unit_list_item_t *first,
                 unit_list_item_t *last)
{
    size_t change = 0;
    unit_list_item_t *tmp;

    if (first != last) {
        /* figure out how many things we are going to move (have to do
         * first, since last might be end and then we wouldn't be able
         * to run the loop)
         */
        for (tmp = first ; tmp != last ; tmp = unit_list_get_next(tmp)) {
            change++;
        }

        unit_list_transfer(pos, first, last);

        /* fix the sizes */
        thislist->unit_list_length += change;
        xlist->unit_list_length -= change;
    }
}


int unit_list_sort(unit_list_t* list, unit_list_item_compare_fn_t compare)
{
    unit_list_item_t* item;
    unit_list_item_t** items;
    size_t i, index=0;

    if (0 == list->unit_list_length) {
        return PMIX_SUCCESS;
    }
    items = (unit_list_item_t**)malloc(sizeof(unit_list_item_t*) *
                                       list->unit_list_length);

    if (NULL == items) {
        return PMIX_ERR_OUT_OF_RESOURCE;
    }

    while(NULL != (item = unit_list_remove_first(list))) {
        items[index++] = item;
    }

    qsort(items, index, sizeof(unit_list_item_t*),
          (int(*)(const void*,const void*))compare);
    for (i=0; i<index; i++) {
        unit_list_append(list,items[i]);
    }
    free(items);
    return PMIX_SUCCESS;
}
