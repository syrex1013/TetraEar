/************************************************************************
*	FILENAME		:	cdec_tet.c
*
*	DESCRIPTION		:	Main routine for speech channel decoding
*
************************************************************************
*
*	SUB-ROUTINES	:	- Channel_Decoding()
*					
************************************************************************
*
*	INCLUDED FILES	:	channel.h
*
************************************************************************/

#include "channel.h"


/**************************************************************************
*
*	ROUTINE			:	Channel_Decoding
*
*	DESCRIPTION			:	Main speech channel decoding function
*
**************************************************************************
*
*	USAGE				:	Channel_Decoding(first,flag,buffer_in, buffer_out)
*						(Routine_Name(input1,input2,input3,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*			INPUT1		:	- Description :	- True only if first call to this routine
*						- Format : Short
*
*			INPUT2		:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*						- Format : Word16**			INPUT3		:	- Description : Frame to be decoded*							- Format : 432 * 16 bit-samples*								   In case of frame stealing , only the second*							   half is decoded**	OUTPUT ARGUMENT(S)	:	
*
*		OUTPUT1		:	- Description : Two concatened speech frames
*						- Format : 274 * 16 bit-samples
*							   In case of frame stealing, only the second
*							   frame is useful
*
*	RETURNED VALUE		:	BFI = 0 --> OK
*						BFI = 1 --> Bad Frame Flag set
*
**************************************************************************/

Word16    Channel_Decoding(short first_pass, Word16 Frame_Stealing,
			Word16 Input_Frame[], Word16 Output_Frame[])
{
Word16  Decoded_array[286];
Word16  badframeindicator;

/* Init for channel-decoder */
	if ( first_pass ) Init_Rcpc_Decoding();

/* Decoding */
	if (!Frame_Stealing)
		Rcpc_Decoding(Frame_Stealing, Input_Frame, Decoded_array);
	else
		Rcpc_Decoding(Frame_Stealing, Input_Frame + 216, Decoded_array);
	badframeindicator = Bfi(Frame_Stealing,Decoded_array);
/* "Decoding" for non-protected class (class 0) */
	Untransform_Class_0(Frame_Stealing,Decoded_array);

	if (!Frame_Stealing)
/* Reordering of the three classes in two speech frames */
		Unbuild_Sensitivity_Classes(Frame_Stealing,Decoded_array,
			Output_Frame);
	else                                               
/* Reordering of the three classes in one speech frame */
		Unbuild_Sensitivity_Classes(Frame_Stealing,Decoded_array,
			Output_Frame + 137);
	return(badframeindicator);
}

