/************************************************************************
*
*	FILENAME		:	cdecoder.c
*
*	DESCRIPTION		:	Main program for speech channel decoding
*
************************************************************************
*
*	USAGE			:	cdecoder input_file output_file
*					(Executable_File Input1 Output1)
*
*	INPUT FILE(S)		:	
*
*		INPUT1	:	- Description : channel encoded serial stream 
*					- Format : binary file 16 bit-samples
*					  each 16 bit-sample represents one encoded bit
*					- 1 channel frame = 432 bits
*
*	OUTPUT FILE(S)	:	
*
*		OUTPUT1	:	- Description :  serial stream output file
*					- Format : binary file 16 bit-samples
*					  each 16 bit-sample represents one encoded bit
*					- 1 output frame includes 2 speech frames with BFI
*					   = 2 * (137 + 1) = 276 bits
*  
*	COMMENTS		:	- Values of channel encoded samples are 
*					either -127 or +127
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



Word16  Frame_stealing = 0;	/* Frame Stealing Flag :
					0 = Inactive, 
					!0 = First Frame in time-slot stolen
					This flag is set/reset by external world */

int	main( int argc, char *argv[] )
{
	FILE    *fin, *fout;
	Word32  Loop_counter = 0;
	short   first_pass = TRUE;
	Word16  i;    
	Word16  bfi1 = 0;            
	Word16  bfi2 = 0;               /* Reset Bad Frame Indicator :
					0 = correct data, 1 = Corrupted frame */
	
	Word16  Reordered_array[286];   /* 2 frames vocoder + 8 + 4 */
	Word16  Interleaved_coded_array[432]; /*time-slot length at 7.2 kb/s*/
	Word16  Coded_array[432];
	
	/* Parse arguments */
	if ( argc != 3 )
	{
		puts( "usage : cdecoder input_file output_file" );
		puts( "format for input_file  : $6B21...114 bits");
		puts( "       ...$6B22...114..." );
		puts( "       ...$6B26...114...$6B21");
		puts( "format for output_file : two 138 (BFI + 137) bit frames");
		exit( 1 );
	}

	if ( (fin = fopen( argv[1], "rb" )) == NULL )
	{
		puts("cdecoder: can't open input_file" );
		exit( 1 );
	}

	if ( (fout = fopen( argv[2], "wb" )) == NULL )
	{
		puts("cdecoder: can't open output_file" );
		exit( 1 );
	}


	while( 1 )
	{
/* read Input_array (1 TETRA frame = 2 speech frames) from input file */
		if (Read_Tetra_File (fin, Interleaved_coded_array) == -1)
		  {
		  puts ("cdecoder: reached end of input_file");
		  break;
		  }
				 



	if (Frame_stealing) 
	{
		Desinterleaving_Signalling(Interleaved_coded_array + 216,
			Coded_array + 216);
/* When Frame Stealing occurs, recopy first half slot : */
		for (i = 0; i < 216; i++) Coded_array[i] = 
			Interleaved_coded_array[i];
	}
	else
		Desinterleaving_Speech(Interleaved_coded_array, Coded_array);
		bfi1 = Frame_stealing;

/* "Interleaved_coded_array" has been desinterleaved and result put
in "Coded_array" */

/* Message in case the Frame was stolen */
		if (bfi1) printf("Frame Nb %ld was stolen\n",Loop_counter+1);

/* Channel Decoding */
		bfi2 = Channel_Decoding(first_pass,Frame_stealing,
				Coded_array,Reordered_array);
		first_pass = FALSE;
		if ((Frame_stealing==0) && (bfi2==1)) bfi1=1;
/* Increment Loop counter */
		Loop_counter++;
/* Message in case the Bad Frame Indicator was set */
		if (bfi2) printf("Frame Nb %ld Bfi active\n\n",Loop_counter);

/* writing  Reordered_array to output file */
			      /* bfi bit */
		if( fwrite( &bfi1, sizeof(short), 1, fout ) != 1 ) {
			puts( "cdecoder: can't write to output_file" );
			break;
		}
			     /* 1st speech frame */
		if( fwrite( Reordered_array, sizeof(short), 137, fout ) != 137 )
		{
			puts( "cdecoder: can't write to output_file" );
			break;
		}
			      /* bfi bit */
		if( fwrite( &bfi2, sizeof(short), 1, fout ) != 1 ) {
			puts( "cdecoder: can't write to output_file" );
			break;
		}
			     /* 2nd speech frame */
		if( fwrite( Reordered_array+137, sizeof(short), 137, fout ) 
					!= 137 ) {
			puts( "cdecoder: can't write to output_file" );
			break;
		}
	}
		
	printf("%ld Channel Frames processed\n",Loop_counter);
	printf("ie %ld Speech Frames\n",2*Loop_counter);
	
	/* closing files */
	fclose( fin );
	fclose( fout );

return (EXIT_SUCCESS);
}

