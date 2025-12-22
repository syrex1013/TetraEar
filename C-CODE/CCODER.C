/************************************************************************
*
*	FILENAME		:	ccoder.c
*
*	DESCRIPTION		:	Main program for speech channel encoding
*
************************************************************************
*
*	USAGE			:	ccoder serial_file cenc_file
*					(Executable_File Input1 Output1)
*
*	INPUT FILE(S)		:	
*
*		INPUT1	:	- Description : serial stream input file 
*					- Format : binary file 16 bit-samples
*					  each 16 bit-sample represents one encoded bit
*					  138 (= 1 + 137) bits per frame
*
*	OUTPUT FILE(S)	:	
*
*		OUTPUT1	:	- Description : channel encoded serial stream 
*					- Format : binary file 16 bit-samples
*					  each 16 bit-sample represents one encoded bit
*
*	COMMENTS		:	- Values of channel encoded samples are 
*					either -127 or +127
*					- 2 input frames are encoded together to produce
*					1 single output frame of 432 samples written in
*					the ouput1 file according to a specific format
*					compatible with the error insertion device
*
************************************************************************
*
*	INCLUDED FILES	:	channel.h
*					stdlib.h
*
************************************************************************/

/* LIBRARIES USED */
#include <stdlib.h>
#include "channel.h"

#ifndef TRUE
# define TRUE   (1==1)
# define FALSE  (1==0)
#endif

Word16  FS_Flag = 0;	/* Frame Stealing Flag :
					 0 = no stealing in the time-slot, 
					!0 = stealing of the first speech frame
							in the time-slot
					This flag is set/reset by external world */


int    main( int argc, char *argv[] )

{
	FILE    *fin, *fout;
	Word32  Loop_counter = 0;
	short   first_pass = TRUE;
	Word16  i;
	Word16  Vocod_array[274];       /* Input Buffer : 2 vocoder frames */
	Word16  Coded_array[432];
	Word16  Interleaved_coded_array[432]; /* Output Buffer */

	/* Parse arguments */
	if ( argc != 3 )
	{
		puts( "usage : ccoder infile outfile" );
		puts( "Channel coding time-slot per time-slot" );
		puts( "format for input file : 138 (BFI + 137) bits frame" );
		puts( "format for output :  $6B21...114 bits...$6B22...114..." );
		puts( "        ...$6B26...114...$6B21");
		exit( 1 );
	}
	if ( (fin = fopen( argv[1], "rb" )) == NULL )
	{
		puts("chanlcod: can't open input file" );
		exit( 1 );
	}
	if ( (fout = fopen( argv[2], "wb" )) == NULL )
	{
		puts("chanlcod: can't open output file" );
		exit( 1 );
	}

	while( 1 )
	{
			      /* Skip over bfi bit */
		if( fread( Vocod_array, sizeof(short), 1, fin ) != 1 ) {
			puts( "chanlcod: reached end of file" );
			break;
		}
			     /* 1st speech frame */
		if( fread( Vocod_array, sizeof(short), 137, fin ) != 137 ) {
			puts( "chanlcod: reached end of file" );
			break;
		}
			      /* Skip over bfi bit */
		if( fread( Vocod_array+137, sizeof(short), 1, fin ) != 1 ) {
			puts( "chanlcod: reached end of file" );
			break;
		}
			     /* 2nd speech frame */
		if( fread( Vocod_array+137, sizeof(short), 137, fin ) != 137 ) {
			puts( "chanlcod: reached end of file" );
			break;
		}


/* Channel Encoding */
		Channel_Encoding(first_pass,FS_Flag,Vocod_array,Coded_array);
		first_pass = FALSE;

/* Interleaving */


	if (!FS_Flag) 	Interleaving_Speech(Coded_array,
							Interleaved_coded_array);
	else	{
		Interleaving_Signalling(	Coded_array + 216,
						Interleaved_coded_array + 216);
		for (i = 0; i < 216; i++)	Interleaved_coded_array[i] =
							Coded_array[i];      
		}
	
/* Increment Loop counter */
		Loop_counter++;

/* write Output_array (1 TETRA frame = 2 speech frames) to output file */
		if (Write_Tetra_File (fout, Interleaved_coded_array) == -1)
		  {
		  puts ("chanlcod: cannot write to output file");
		  break;
		  }
	}
	printf("%ld Speech Frames processed\n",2*Loop_counter);
	printf("ie %ld Channel Frames\n",Loop_counter);
	
	/* closing files */
	fclose( fin );
	fclose( fout );

return (EXIT_SUCCESS);
}

