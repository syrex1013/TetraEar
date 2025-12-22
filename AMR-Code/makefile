########################################################################
#
#	FILENAME		:	makefile
#
#	DESCRIPTION		:	Usable for the compilation of the C code
#					(UNIX environment)
#
#	LANGUAGE		:	ANSI-C
#
########################################################################
#
#	COMMENTS		:	Command line to be used (without the brackets)
#
#					- "make scoder"	: to compile the source coder
#					- "make ccoder"	: to compile the channel coder
#					- "make"		: to compile all 
#
########################################################################

# macro definitions

CC=gcc

CFLAGS	=	-g -I.

SRCS1		=	ccoder.c	ccod_tet.c	init_params.c	sub_cc.c \
			tetra_op.c

SRCS2		=	cdecoder.c	cdec_tet.c	init_params.c	sub_cd.c \
			tetra_op.c

# target definitions

all:		ccoder	cdecoder

ccoder:
	$(CC) $(SRCS1) $(CFLAGS) -o ccoder

cdecoder:
	$(CC) $(SRCS2) $(CFLAGS) -o cdecoder

clean:
	rm -f ccoder cdecoder core *.o

