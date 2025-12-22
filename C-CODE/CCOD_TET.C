/************************************************************************
*	FILENAME		:	ccod_tet.c
*
*	DESCRIPTION		:	Main routine for speech channel encoding
*
************************************************************************
*
*	SUB-ROUTINES	:	- Channel_Encoding()
*					
************************************************************************
*
*	INCLUDED FILES	:	channel.h
*					const.tab
*
************************************************************************/

#include "channel.h"
#include "const.tab"


/**************************************************************************
*
*	ROUTINE			:	Channel_Encoding
*
*	DESCRIPTION			:	Main speech channel coding function
*
**************************************************************************
*
*	USAGE				:	Channel_Encoding(first,flag,buffer_in, buffer_out)
*						(Routine_Name(input1,input2,input3,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*			INPUT1		:	- Description :	- True only if first call to this routine
*						- Format : Short
*
*			INPUT2		:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*						- Format : Word16**		INPUT3		:	- Description : two concatened speech frames*						- Format : 274 * 16 bit-samples*							   In case of frame stealing, only the second
*							  	   frame is encoded
*
*	OUTPUT ARGUMENT(S)	:	
*
*		OUTPUT1		:	- Description : encoded frame
*							- Format : 432 * 16 bit-samples
*								   In case of frame stealing , only the second
*							   half is filled
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void Channel_Encoding(short first_pass, Word16 Frame_Stealing, Word16 Input_Frame[], Word16 Output_Frame[])

{

Word16  Ordered_array[286];     /* 2 vocoder frames + 8 + 4 */
Word16  i, Nber_Info_Bits;

/* Init for channel encoder */
		if (!Frame_Stealing)
			Nber_Info_Bits = N0_2 + N1_2 + N2_2 + SIZE_CRC;
		else 
			Nber_Info_Bits = N0 + N1 + N2 + Fs_SIZE_CRC; 
			
		if ( first_pass ) Init_Rcpc_Coding(Frame_Stealing,
					Ordered_array);  
		else {  /* Zero the (K - 1) last bits of Ordered_array */
			for (i = 0; i < K - 1; i++)
				Ordered_array[Nber_Info_Bits++] = 0;
		}

		if (!Frame_Stealing)
/* Ordering of the two speech frames in three classes */
			Build_Sensitivity_Classes(Frame_Stealing, Input_Frame,
					Ordered_array);
		else
/* Ordering of the second speech frame in three classes */
			Build_Sensitivity_Classes(Frame_Stealing,
					Input_Frame + 137, Ordered_array);


/* "Coding" for non-protected class (class 0) : 0 --> 127, 1 --> -127 */
		Transform_Class_0(Frame_Stealing, Ordered_array);

/* CRC computation on the last class (most sensitive bits) */
		Build_Crc(Frame_Stealing, Ordered_array);

		if (!Frame_Stealing)
/* Channel encoding of the 2 frames */
			Rcpc_Coding(Frame_Stealing, Ordered_array, Output_Frame);
		else
/* Channel encoding of 2nd frame */
			Rcpc_Coding(Frame_Stealing, Ordered_array,
					Output_Frame + 216);

		return;
}

