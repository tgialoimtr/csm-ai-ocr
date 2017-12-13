package csmai.controller;

import java.io.BufferedWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Controller;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.ModelAndView;

import csmai.model.OcrResult;
import csmai.service.ReadService;


@Controller
public class ApiController {

	@Value("${ocr.upload.dir}")
	String uploadDir;
	
    @RequestMapping("/")
    public String index() {
    	return "index";
    }
    
    @Autowired
    private ReadService reader;
    
    @RequestMapping(method = RequestMethod.POST, value = "/ocr/read/")
    @ResponseBody
    public String handleCleanImage(@RequestParam("file") List<MultipartFile> files) {
        long start = System.currentTimeMillis();
        OcrResult rs = new OcrResult();
        rs.result = "Internal server error";
        if (files.isEmpty()) {
            return "File is empty";
        }
		for (MultipartFile file : files) {
            String fileName = start + "_" + file.getOriginalFilename();
            Path filePath = Paths.get(uploadDir + fileName);
            try {
            	Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);
            	rs = reader.read(filePath.toString());
            } catch (Exception e) {
            	e.printStackTrace();
            }
            
		}
		System.out.println(rs.result);
		return rs.result;
    }
}
