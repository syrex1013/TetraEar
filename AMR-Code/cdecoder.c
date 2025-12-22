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
#include "globals.h"
		       
#ifndef TRUE
# define TRUE   (1==1)
# define FALSE  (1==0)
#endif


#define GUARD   400


Word16  FRAME_STEALING=FALSE;


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
	Word16  bfi2 = 0;               
	Word16  bfi3 = 0;               /* Reset Bad Frame Indicator :
					0 = correct data, 1 = Corrupted frame */
	Word16  mode;
	Word16  Reordered_array[274+12+GUARD];   /* 2 frames vocoder + 8 + 4 */
	Word16  Interleaved_coded_array[432]; /*time-slot length at 7.2 kb/s*/
	Word16  Coded_array[432];
	Word16  Zeros[250];
	
	for (i=0; i<250; i++)
	  Zeros[i] = 0;
	
	/* Parse arguments */
	if (( argc < 3 ) || ( argc > 5 ))
	{
		puts( "usage : cdecoder input_file output_file [CoderType [S]]" );
		puts( "format for input_file  : $6B21...114 bits");
		puts( "       ...$6B22...114..." );
		puts( "       ...$6B26...114...$6B21");
		puts( "format for output_file : two 138 (BFI + 137) bit frames");
		puts( "CoderType = 0 - TETRA (default)");
		puts( "            1 - AMR475 ");
		puts( "S = Stealing at 10% of TDMA Frames ");
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

	if (argc >= 4)
	{
		CoderType = atoi(argv[3]);
		if (( CoderType < 0 ) || ( CoderType > 1 ))
		{
			puts("chanlcod: Illegal value of CoderType" );
			exit( 1 );
		}
		
	        if (argc > 4)
		{
		  if (argv[4][0] == 'S')
		    FRAME_STEALING = TRUE;
		}
	}
	else
        	CoderType = 0;
        init_params(CoderType);
        
	while( 1 )
	{
	        if (FRAME_STEALING)
	          Frame_stealing = ((Loop_counter%10) == 2);
	        
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

/* "Interleaved_coded_array" has been desinterleaved and result put
in "Coded_array" */

/* Channel Decoding */
	        if (CoderType == 0)     /* TETRA  */
                {
                    /* Message in case the Frame was stolen */
		    if (Frame_stealing) printf("Frame Nb %ld was stolen\n",Loop_counter+1);

                    bfi1 = Frame_stealing;
		    bfi2 = Channel_Decoding(first_pass,Frame_stealing,
				Coded_array,Reordered_array);

		    if ((Frame_stealing==0) && (bfi2==1)) bfi1=1;
/* Message in case the Bad Frame Indicator was set */
		    if (bfi2) printf("Frame Nb %ld Bfi active\n\n",Loop_counter+1);
                }
                else
                {
                    /* Message in case the Frame was stolen */
		    if (Frame_stealing) printf("Frame Nb %ld was stolen\n",Loop_counter+1);

                    bfi2 = Frame_stealing;
		    bfi1 = Channel_Decoding(first_pass,Frame_stealing,
				Coded_array,Reordered_array);

		    if ((Frame_stealing==0) && (bfi1==1)) bfi2=1;
/* Message in case the Bad Frame Indicator was set */
		    if (bfi1) printf("Frame Nb %ld Bfi active\n\n",Loop_counter+1);
                }

		first_pass = FALSE;
/* Increment Loop counter */
		Loop_counter++;

/* writing  Reordered_array to output file */
			      /* bfi bit */
	        if (CoderType == 0)     /* TETRA  */
	        {
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
		else    /* AMR Modes  */
		{
		    mode = CoderType - 1;
		    if (bfi1) bfi3 = 3; else bfi3 = 0;
		    if( fwrite( &bfi3, sizeof(short), 1, fout ) != 1 ) {
			puts( "cdecoder: can't write to output_file" );
			break;
		    }
			     /* 1st speech frame */
		    if( fwrite( Reordered_array, sizeof(short), Length_vocoder_frame, fout ) !=  Length_vocoder_frame)
		    {
			puts( "cdecoder: can't write to output_file" );
		    	break;
		    }
		    fwrite( Zeros, sizeof(short), 244 - Length_vocoder_frame, fout ); 
		    fwrite( &mode, sizeof(short), 1, fout );
		    fwrite( Zeros, sizeof(short), 4, fout ); 
		    
		    if (bfi1) bfi3 = 3; else bfi3 = 0;
		    if( fwrite( &bfi3, sizeof(short), 1, fout ) != 1 ) {
			puts( "cdecoder: can't write to output_file" );
			break;
		    }
			     /* 2nd speech frame */
		    if( fwrite( Reordered_array+Length_vocoder_frame, sizeof(short), Length_vocoder_frame, fout ) != Length_vocoder_frame )
		    {
			puts( "cdecoder: can't write to output_file" );
		    	break;
		    }
		    fwrite( Zeros, sizeof(short), 244 - Length_vocoder_frame, fout ); 
		    fwrite( &mode, sizeof(short), 1, fout ); 
		    fwrite( Zeros, sizeof(short), 4, fout ); 
		    
		    if (bfi2) bfi3 = 3; else bfi3 = 0;
		    if( fwrite( &bfi3, sizeof(short), 1, fout ) != 1 ) {
			puts( "cdecoder: can't write to output_file" );
			break;
		    }
			     /* 3rd speech frame */
		    if( fwrite( Reordered_array+2*Length_vocoder_frame, sizeof(short), Length_vocoder_frame, fout ) !=  Length_vocoder_frame)
		    {
			puts( "cdecoder: can't write to output_file" );
		    	break;
		    }
		    fwrite( Zeros, sizeof(short), 244 - Length_vocoder_frame, fout ); 
		    fwrite( &mode, sizeof(short), 1, fout ); 
		    fwrite( Zeros, sizeof(short), 4, fout ); 
		}
	}
		
	printf("%ld Channel Frames processed\n",Loop_counter);
	printf("ie %ld Speech Frames\n",SpFrms_per_TDMFrm*Loop_counter);
	
	/* closing files */
	fclose( fin );
	fclose( fout );

return (EXIT_SUCCESS);
}

