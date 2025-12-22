/************************************************************************
*
*	FILENAME		:	scoder.c
*
*	DESCRIPTION		:	Main program for speech source encoding
*
************************************************************************
*
*	USAGE			:	scoder  speech_file  serial_file  synth_file
*					(executable_file input1 output1 output2)
*
*	INPUT FILE(S)		:	
*
*		INPUT1	:	- Description : speech file to be analyzed
*					- Format : binary file 16 bit-samples
*					  240 samples per frame
*
*
*	OUTPUT FILE(S)	:	
*
*		OUTPUT1	:	- Description : serial stream output file 
*					- Format : binary file 16 bit-samples
*					  each 16 bit-sample represents one encoded bit
*					  138 (= 1 + 137) bits per frame
*
*		OUTPUT2	:	- Description : local synthesis output file 
*					- Format : binary file 16 bit-samples
*
*	COMMENTS		:	First sample of each OUTPUT1 frame is forced to zero
*
************************************************************************
*
*	INCLUDED FILES	:	source.h
*					stdio.h
*					stdlib.h
*
************************************************************************/

#include <stdio.h>
#include <stdlib.h>

#include "source.h"

/*-----------------*
 * Constants       *
 *-----------------*/

#define L_frame     240
#define serial_size 138
#define ana_size     23


int main(int argc, char *argv[] )
{
  Word16 frame;

  extern Word16 *new_speech;		/* Pointer on new_speech. */

  Word16 syn[L_frame];			/* Local synthesis.       */
  Word16 ana[ana_size];			/* Analysis parameters.   */
  Word16 serial[serial_size];		/* Serial stream.         */

  FILE  *f_speech, *f_syn, *f_serial;

  /* Passed arguments */

  if ( argc != 4 )
  {
     printf("Usage : scoder  speech_file  serial_file  synth_file\n");
     printf("\n");
     printf("Format for speech_file:\n");
     printf("  Speech is read form a binary file of 16 bits data.\n");
     printf("\n");
     printf("Format for serial_file:\n");
     printf("  Serial stream output is written to a binary file\n");
     printf("  where each 16-bit word represents 1 encoded bit.\n");
     printf("  BFI(=0) + 137 bits by frame\n");
     printf("\n");
     printf("Format for synth_file:\n");
     printf("  Local synthesis is written to a binary file of 16 bits data.\n");
     exit( 1 );
  }

  /* Open files for speech, serial stream and local synthesis */

  if( (f_speech = fopen(argv[1],"rb") ) == NULL )
  {
    printf("Input file '%s' does not exist !!\n", argv[1]);
    exit(0);
  }


  if( (f_serial = fopen(argv[2], "wb") ) == NULL )
  {
    printf("Cannot open file '%s' !!\n", argv[2]);
    exit(0);
  }

  if( (f_syn = fopen(argv[3], "wb") ) == NULL )
  {
    printf("Cannot open file '%s' !!\n", argv[3]);
    exit(0);
  }

  /* Initialization of the coder */

  Init_Pre_Process();
  Init_Coder_Tetra();

  /* Loop for each "L_frame" speech data. */

  frame =0;
  while( fread(new_speech, sizeof(Word16), L_frame, f_speech) == L_frame)
  {
    printf("frame=%d\n", ++frame);

    Pre_Process(new_speech, (Word16)L_frame);	/* Pre processing of input 
											 speech */

    Coder_Tetra(ana, syn);              /* Find speech parameters         */

    Post_Process(syn, (Word16)L_frame); /* Post processing of synthesis   */

    Prm2bits_Tetra(ana, serial);        /* Parameters to serial bits      */

    fwrite(syn,    sizeof(Word16), L_frame    ,  f_syn);
    fwrite(serial, sizeof(Word16), serial_size,  f_serial);
  }

  return (EXIT_SUCCESS);
}

